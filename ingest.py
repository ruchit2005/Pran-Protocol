import logging
from pathlib import Path
from typing import Optional
import argparse

# Updated import path
from config.settings import settings
from src.document_processor.loader import DocumentLoader
from src.document_processor.chunker import OptimizedChunker
from src.vector_store.chroma_manager import ChromaDBManager

# Optional: Google Drive client (only needed for gdrive ingestion)
try:
    from src.document_processor.gdrive_client import GoogleDriveClient
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False
    GoogleDriveClient = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ingest_from_google_drive(folder_id: str, collection_name: Optional[str] = None):
    """Downloads files from GDrive and ingests them."""
    if not GDRIVE_AVAILABLE:
        logger.error("Google Drive client not available. Install required packages: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return 0
    
    logger.info(f"Starting ingestion from Google Drive folder: {folder_id}")
    gdrive_client = GoogleDriveClient()
    
    # Download files to the raw data directory
    downloaded_files = gdrive_client.download_all_files(folder_id)
    if not downloaded_files:
        logger.warning("No files were downloaded from Google Drive.")
        return 0
    
    logger.info(f"Downloaded {len(downloaded_files)} files. Now processing...")
    # Ingest the newly downloaded files from the local raw directory
    return ingest_local_documents(settings.RAW_DATA_DIR, collection_name=collection_name)


def ingest_local_documents(directory: Path, collection_name: Optional[str] = None) -> int:
    """
    Ingest documents from a local directory into the vector store.
    
    Args:
        directory: Path to the directory containing documents.
        collection_name: Optional specific collection name (yoga, ayush, etc.)
    
    Returns:
        Number of document chunks ingested.
    """
    logger.info(f"Starting ingestion from local directory: {directory}")
    
    # 1. Load documents
    documents = DocumentLoader.load_documents_from_directory(directory)
    if not documents:
        logger.warning("No documents found to ingest.")
        return 0
    logger.info(f"Loaded {len(documents)} document pages.")
    
    # 2. Chunk documents
    chunker = OptimizedChunker(strategy=settings.CHUNKING_STRATEGY)
    chunks = chunker.chunk_documents(documents)
    logger.info(f"Created {len(chunks)} chunks using '{settings.CHUNKING_STRATEGY}' strategy.")
    
    # 3. Add to vector store (domain-specific or general)
    chroma_manager = ChromaDBManager(collection_name=collection_name)
    num_added = chroma_manager.add_documents(chunks)
    
    collection_display = collection_name or settings.CHROMA_COLLECTION_NAME
    logger.info(f"Successfully added {num_added} chunks to ChromaDB collection '{collection_display}'.")
    
    return num_added

def reset_database(collection_name: Optional[str] = None):
    """Deletes a ChromaDB collection."""
    collection_display = collection_name or settings.CHROMA_COLLECTION_NAME
    logger.warning(f"Resetting database by deleting collection '{collection_display}'...")
    chroma_manager = ChromaDBManager(collection_name=collection_name)
    chroma_manager.delete_collection()
    logger.info("Database collection deleted successfully.")

def main():
    """Main CLI interface for ingestion."""
    parser = argparse.ArgumentParser(description="Knowledge Base Ingestion for Healthcare RAG Agent")
    parser.add_argument('command', choices=['ingest-local', 'ingest-gdrive', 'reset'], help='Command to execute')
    parser.add_argument('--directory', help='Local directory path for ingestion', default=str(settings.RAW_DATA_DIR))
    parser.add_argument('--folder-id', help='Google Drive folder ID for ingestion')
    parser.add_argument('--collection', help='Collection name (yoga, ayush, mental_wellness, symptoms, schemes)', default=None)
    
    args = parser.parse_args()
    
    # Validate collection name if provided
    valid_collections = list(settings.COLLECTION_NAMES.keys())
    if args.collection and args.collection not in valid_collections:
        print(f"❌ Error: Invalid collection name. Valid options: {', '.join(valid_collections)}")
        return
    
    collection_name = settings.COLLECTION_NAMES.get(args.collection) if args.collection else None
    
    if args.command == 'ingest-local':
        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Error: Directory '{directory}' not found.")
            return
        
        collection_display = args.collection or "general"
        print(f"\n📂 Ingesting documents into '{collection_display}' collection...")
        num_docs = ingest_local_documents(directory, collection_name=collection_name)
        print(f"\n✅ Ingestion complete. Added {num_docs} document chunks to the knowledge base.")

    elif args.command == 'ingest-gdrive':
        if not GDRIVE_AVAILABLE:
            print("❌ Error: Google Drive integration not available.")
            print("Install required packages: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return
        
        if not args.folder_id:
            print("❌ Error: --folder-id is required for the ingest-gdrive command.")
            return
        if not settings.GDRIVE_CREDENTIALS_PATH.exists():
            print(f"❌ Error: Google Drive credentials not found at {settings.GDRIVE_CREDENTIALS_PATH}")
            print("Please set up your 'credentials.json' file in the 'config' directory.")
            return
        
        collection_display = args.collection or "general"
        print(f"\n📂 Ingesting documents from Google Drive into '{collection_display}' collection...")
        num_docs = ingest_from_google_drive(args.folder_id, collection_name=collection_name)
        print(f"\n✅ Ingestion complete. Added {num_docs} document chunks from Google Drive.")
    
    elif args.command == 'reset':
        collection_display = args.collection or "general"
        confirm = input(f"⚠️  Are you sure you want to RESET the '{collection_display}' collection? This cannot be undone. (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database(collection_name=collection_name)
            print(f"\n✅ Collection '{collection_display}' reset complete.")
        else:
            print("\n❌ Reset cancelled.")

if __name__ == "__main__":
    main()