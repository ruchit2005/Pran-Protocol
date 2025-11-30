"use client";
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Heart, Send, Sparkles, Activity, Loader2, Plus, MessageSquare, LogOut, Menu, X } from 'lucide-react';
import VoiceRecorder from "./VoiceRecorder";

type Message = {
  role: 'user' | 'assistant';
  content: string | React.ReactNode;
};

type Session = {
  id: number;
  title: string;
  created_at: string;
};

type HistoryItem = {
  query: string;
  intent: string;
};

const formatResponse = (response: any): React.ReactNode => {
  const { intent, reasoning, output, yoga_recommendations, yoga_videos } = response;

  const renderContent = (content: any) => {
    if (typeof content === 'string') {
      return content.split('\n').map((line, i) => (
        <p key={i} className="mb-2 last:mb-0">{line}</p>
      ));
    }
    if (content?.message) {
      return (
        <div>
          <p className="font-medium">{content.message}</p>
          {content.emergency && (
            <p className="text-red-400 mt-2 font-semibold">⚠️ This is an emergency.</p>
          )}
        </div>
      );
    }
    return <pre className="text-sm overflow-x-auto">{JSON.stringify(content, null, 2)}</pre>;
  };

  return (
    <div className="space-y-3">
      {intent && (
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full w-fit">
          <Sparkles className="w-3 h-3" />
          <span className="font-medium">{intent?.replace(/_/g, ' ')}</span>
        </div>
      )}
      {output && (
        <div className="prose prose-invert max-w-none">
          {renderContent(output)}
        </div>
      )}
      {yoga_recommendations && (
        <div className="mt-4 p-4 from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/20">
          <h4 className="font-semibold text-purple-300 mb-3 flex items-center gap-2">
            🧘 Yoga Recommendations
          </h4>
          <div className="text-gray-200">
            {renderContent(yoga_recommendations)}
          </div>
        </div>
      )}
      {yoga_videos && Array.isArray(yoga_videos) && yoga_videos.length > 0 && (
        <div className="mt-4">
          <h4 className="font-semibold text-red-300 mb-3 flex items-center gap-2">
            📺 Recommended Videos
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {yoga_videos.map((video: any, idx: number) => (
              <a
                key={idx}
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-colors border border-white/10"
              >
                {video.thumbnail && (
                  <img src={video.thumbnail} alt={video.title} className="w-full h-32 object-cover rounded-lg mb-2" />
                )}
                <p className="text-sm font-medium text-white line-clamp-2">{video.title}</p>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function HealthcareChat() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // Mobile sidebar toggle

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check Auth & Fetch Sessions
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    fetchSessions(token);
  }, []);

  const fetchSessions = async (token: string) => {
    try {
      const res = await fetch("/api/sessions", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  const loadSession = async (sessionId: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setCurrentSessionId(sessionId);
    setIsSidebarOpen(false); // Close sidebar on mobile

    try {
      const res = await fetch(`/api/sessions/${sessionId}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const history = await res.json();
        // Convert DB history to UI messages
        const uiMessages = history.map((msg: any) => {
          // Try to parse assistant content if it's JSON
          let content = msg.content;
          if (msg.role === 'assistant') {
            try {
              // If it looks like JSON, parse it for formatResponse
              if (content.trim().startsWith('{')) {
                content = formatResponse(JSON.parse(content));
              }
            } catch (e) {
              // Keep as string
            }
          }
          return { role: msg.role, content };
        });
        setMessages(uiMessages);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const createNewSession = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setMessages([{
      role: 'assistant',
      content: (
        <div className="space-y-3">
          <p className="text-lg">👋 Hello! I'm your Healthcare Assistant.</p>
          <p className="text-gray-300">How can I help you today?</p>
        </div>
      )
    }]);
    setCurrentSessionId(null);
    setIsSidebarOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInput('');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: input,
          session_id: currentSessionId
        }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();

      // If this was a new session, refresh session list
      if (!currentSessionId) {
        fetchSessions(token);
        // Ideally backend returns the new session ID in the response or we re-fetch the latest session
        // For now, simple re-fetch is okay.
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: formatResponse(data),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to fetch:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-white overflow-hidden">

      {/* Sidebar (Desktop & Mobile) */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-950 border-r border-white/10 transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 flex flex-col`}>
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-emerald-400">
            <Heart className="w-5 h-5" fill="currentColor" />
            <span>DeepShiva</span>
          </div>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-400">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4">
          <button
            onClick={createNewSession}
            className="w-full flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-xl transition-colors font-medium"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => loadSession(session.id)}
              className={`w-full text-left px-3 py-3 rounded-lg text-sm flex items-center gap-3 transition-colors ${currentSessionId === session.id ? 'bg-white/10 text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}
            >
              <MessageSquare className="w-4 h-4 shrink-0" />
              <span className="truncate">{session.title}</span>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-white/10">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 text-gray-400 hover:text-red-400 px-3 py-2 rounded-lg transition-colors text-sm"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative">

        {/* Header */}
        <header className="bg-white/5 backdrop-blur-xl border-b border-white/10 px-4 py-3 shadow-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setIsSidebarOpen(true)} className="md:hidden text-gray-300">
              <Menu className="w-6 h-6" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-white">Healthcare Assistant</h1>
              <p className="text-xs text-emerald-300 flex items-center gap-1">
                <Activity className="w-3 h-3" />
                AI-Powered • Secure • Private
              </p>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-hidden relative">
          <div className="h-full max-w-4xl mx-auto px-4 py-6 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {messages.length === 0 && !currentSessionId && (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 space-y-4">
                <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-emerald-400" />
                </div>
                <p className="text-lg font-medium text-white">How can I assist you today?</p>
              </div>
            )}

            <div className="space-y-6 pb-4">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                >
                  <div className="flex gap-3 max-w-[85%]">
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 from-emerald-400 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg shrink-0">
                        <Heart className="w-4 h-4 text-white" fill="white" />
                      </div>
                    )}
                    <div
                      className={`rounded-2xl p-4 shadow-lg ${msg.role === 'user'
                          ? 'from-blue-500 to-cyan-500 bg-gradient-to-r text-white ml-auto'
                          : 'bg-white/10 backdrop-blur-xl text-gray-100 border border-white/10'
                        }`}
                    >
                      <div className="text-sm leading-relaxed">{msg.content}</div>
                    </div>
                    {msg.role === 'user' && (
                      <div className="w-8 h-8 from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg shrink-0">
                        <span className="text-white font-semibold text-xs">You</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start animate-fadeIn">
                  <div className="flex gap-3 max-w-[85%]">
                    <div className="w-8 h-8 from-emerald-400 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg">
                      <Heart className="w-4 h-4 text-white" fill="white" />
                    </div>
                    <div className="rounded-2xl p-4 bg-white/10 backdrop-blur-xl border border-white/10 shadow-lg">
                      <div className="flex items-center gap-2 text-gray-300">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Analyzing...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="bg-white/5 backdrop-blur-xl border-t border-white/10 px-4 py-4 shadow-2xl">
          <div className="max-w-4xl mx-auto flex gap-3 items-end">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="w-full px-5 py-3.5 rounded-2xl bg-white/10 backdrop-blur-sm text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-400/50 focus:border-emerald-400/50 placeholder-gray-400 transition-all"
                placeholder="Ask about health schemes, ayurveda, symptoms..."
                disabled={isLoading}
              />
            </div>

            <VoiceRecorder
              onTranscribed={(text, assistant) => {
                const userMessage: Message = { role: "user", content: text };
                setMessages((prev) => [...prev, userMessage]);

                if (assistant) {
                  const assistantMessage: Message = {
                    role: "assistant",
                    content: formatResponse(assistant),
                  };
                  setMessages((prev) => [...prev, assistantMessage]);
                }
                setIsLoading(false);
                setInput("");
              }}
              onError={(err) => {
                console.error("Voice error:", err);
              }}
            />

            <button
              onClick={handleSubmit}
              className="px-4 py-3.5 from-emerald-500 to-cyan-500 bg-gradient-to-r hover:from-emerald-600 hover:to-cyan-600 text-white rounded-2xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg"
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">
            This assistant provides general information. Always consult healthcare professionals.
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.4s ease-out; }
      `}</style>
    </div>
  );
}
