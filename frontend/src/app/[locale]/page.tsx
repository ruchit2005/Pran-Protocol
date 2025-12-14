import Chat from '@/components/chat';

export default function Home() {
  return (
    // The Chat component now controls the full screen background
    <main className="h-screen w-full bg-[#FDFCF8]">
      <Chat />
    </main>
  );
}