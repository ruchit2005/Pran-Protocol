// In frontend/src/app/page.tsx
import Chat from '@/components/chat';

export default function Home() {
  return (
    <main className="bg-gray-900 text-white min-h-screen">
      <Chat />
    </main>
  );
}