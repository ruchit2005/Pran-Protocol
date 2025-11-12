import logging
from pathlib import Path
from typing import Optional
import argparse

# Updated import path
from src.config import settings
from src.document_processor.loader import DocumentLoader
from src.document_processor.chunker import OptimizedChunker
from src.vector_store.chroma_manager import ChromaDBManager
from src.document_processor.gdrive_client import GoogleDriveClient

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

def ingest_from_google_drive(folder_id: str):
    """Downloads files from GDrive and ingests them."""
    logger.info(f"Starting ingestion from Google Drive folder: {folder_id}")
    gdrive_client = GoogleDriveClient()
    
    # Download files to the raw data directory
    downloaded_files = gdrive_client.download_all_files(folder_id)
    if not downloaded_files:
        logger.warning("No files were downloaded from Google Drive.")
        return 0
    
    logger.info(f"Downloaded {len(downloaded_files)} files. Now processing...")
    # Ingest the newly downloaded files from the local raw directory
    return ingest_local_documents(settings.RAW_DATA_DIR)


def ingest_local_documents(directory: Path) -> int:
    """
    Ingest documents from a local directory into the vector store.
    
    Args:
        directory: Path to the directory containing documents.
    
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
    
    # 3. Add to vector store
    chroma_manager = ChromaDBManager()
    num_added = chroma_manager.add_documents(chunks)
    logger.info(f"Successfully added {num_added} chunks to ChromaDB collection '{settings.CHROMA_COLLECTION_NAME}'.")
    
    return num_added

def reset_database():
    """Deletes the entire ChromaDB collection."""
    logger.warning(f"Resetting database by deleting collection '{settings.CHROMA_COLLECTION_NAME}'...")
    chroma_manager = ChromaDBManager()
    chroma_manager.delete_collection()
    logger.info("Database collection deleted successfully.")

def main():
    """Main CLI interface for ingestion."""
    parser = argparse.ArgumentParser(description="Knowledge Base Ingestion for Healthcare RAG Agent")
    parser.add_argument('command', choices=['ingest-local', 'ingest-gdrive', 'reset'], help='Command to execute')
    parser.add_argument('--directory', help='Local directory path for ingestion', default=str(settings.RAW_DATA_DIR))
    parser.add_argument('--folder-id', help='Google Drive folder ID for ingestion')
    
    args = parser.parse_args()
    
    if args.command == 'ingest-local':
        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Error: Directory '{directory}' not found.")
            return
        
        num_docs = ingest_local_documents(directory)
        print(f"\n✅ Ingestion complete. Added {num_docs} document chunks to the knowledge base.")

    elif args.command == 'ingest-gdrive':
        if not args.folder_id:
            print("❌ Error: --folder-id is required for the ingest-gdrive command.")
            return
        if not settings.GDRIVE_CREDENTIALS_PATH.exists():
            print(f"❌ Error: Google Drive credentials not found at {settings.GDRIVE_CREDENTIALS_PATH}")
            print("Please set up your 'credentials.json' file in the 'config' directory.")
            return
            
        num_docs = ingest_from_google_drive(args.folder_id)
        print(f"\n✅ Ingestion complete. Added {num_docs} document chunks from Google Drive.")
    
    elif args.command == 'reset':
        confirm = input("⚠️  Are you sure you want to RESET the entire knowledge base? This cannot be undone. (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
            print("\n✅ Knowledge base reset complete.")
        else:
            print("\n❌ Reset cancelled.")

if __name__ == "__main__":
    main()