"use client";
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import {
  Leaf, Send, Sparkles, Loader2, Plus, MessageCircle,
  LogOut, Menu, X, Volume2, Pause, Play, ChevronLeft,
  ChevronRight, Youtube, Activity, User
} from 'lucide-react';
import VoiceRecorder from "./VoiceRecorder";

// --- Types ---
type Message = {
  role: 'user' | 'assistant';
  content: string | React.ReactNode;
  rawContent?: string;
  audioUrl?: string;
};

type Session = {
  id: string;  // Changed from number to match MongoDB ObjectId
  title: string;
  created_at: string;
};



interface ChatResponse {
  intent?: string;
  output?: string | { message: string; emergency?: boolean };
  yoga_videos?: Array<{ title: string; url: string; thumbnail?: string }>;
  yoga_recommendations?: string;
}

const formatResponse = (response: ChatResponse): React.ReactNode => {
  const { intent, output, yoga_videos, yoga_recommendations } = response;

  const renderContent = (content: string | { message: string; emergency?: boolean } | unknown) => {
    if (typeof content === 'string') {
      return (
        <div className="prose prose-stone max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0 text-stone-700 leading-relaxed">{children}</p>,
              h1: ({ children }) => <h1 className="text-2xl font-bold text-stone-800 mb-3">{children}</h1>,
              h2: ({ children }) => <h2 className="text-xl font-bold text-stone-800 mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-lg font-semibold text-stone-800 mb-2">{children}</h3>,
              strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 ml-4">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 ml-4">{children}</ol>,
              li: ({ children }) => <li className="text-stone-700">{children}</li>,
              code: ({ children }) => <code className="bg-stone-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      );

    }
    if (content && typeof content === 'object' && 'message' in content) {
      const msgContent = content as { message: string; emergency?: boolean };
      return (
        <div>
          <p className="font-medium text-stone-800">{msgContent.message}</p>
          {msgContent.emergency && (
            <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg flex items-start gap-2 text-red-600">
              <Activity className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="font-semibold text-sm">Emergency Warning: {msgContent.emergency}</p>
            </div>
          )}
        </div>
      );
    }
    return <pre className="text-xs bg-stone-100 p-2 rounded overflow-x-auto">{JSON.stringify(content, null, 2)}</pre>;
  };

  return (
    <div className="space-y-4 font-sans">
      {intent && (
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-pale/30 text-primary-light text-xs font-semibold uppercase tracking-wider">
          <Sparkles className="w-3 h-3" />
          <span>{intent.replace(/_/g, ' ')}</span>
        </div>
      )}

      {output && (
        <div className="prose prose-stone max-w-none">
          {renderContent(output)}
        </div>
      )}

      {yoga_recommendations && (
        <div className="mt-4 p-5 bg-[#F2E8CF]/30 rounded-xl border border-[#F2E8CF] shadow-sm">
          <h4 className="font-serif text-primary font-bold mb-3 flex items-center gap-2 text-lg">
            <Leaf className="w-5 h-5" />
            Yoga Recommendations
          </h4>
          <div className="text-stone-700">
            {renderContent(yoga_recommendations)}
          </div>
        </div>
      )}


      {yoga_videos && Array.isArray(yoga_videos) && yoga_videos.length > 0 && (
        <div className="mt-4">
          <h4 className="font-serif text-stone-800 font-bold mb-3 flex items-center gap-2">
            <Youtube className="w-5 h-5 text-red-500" />
            Curated Videos for You
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {yoga_videos.map((video, idx: number) => (
              <a
                key={idx}
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block overflow-hidden bg-white rounded-xl shadow-sm hover:shadow-organic transition-all border border-stone-200 hover:border-primary-light/30"
              >
                {video.thumbnail && (
                  <div className="relative overflow-hidden aspect-video">
                    <img
                      src={video.thumbnail}
                      alt={video.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors" />
                    <div className="absolute bottom-2 right-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded">
                      Watch
                    </div>
                  </div>
                )}
                <div className="p-3">
                  <p className="text-sm font-semibold text-stone-800 line-clamp-2 group-hover:text-primary transition-colors">
                    {video.title}
                  </p>
                </div>
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

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<{
    email: string;
    display_name?: string;
    photo_url?: string;
  } | null>(null);

  // UI State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Desktop default open
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Audio State
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isAudioLoading, setIsAudioLoading] = useState<number | null>(null);

  // Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // --- Effects ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    fetchSessions(token);
    fetchUserProfile(token);

    // Auto-collapse sidebar on small screens
    const handleResize = () => {
      if (window.innerWidth < 768) setIsSidebarOpen(false);
      else setIsSidebarOpen(true);
    };

    handleResize(); // Initial check
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [router]);


  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // --- API Functions ---
  const fetchUserProfile = async (token: string) => {
    try {
      const res = await fetch("/api/profile", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const profile = await res.json();
        console.log("User profile loaded:", profile);
        setUserProfile(profile);
      } else {
        console.error("Failed to fetch profile:", res.status, await res.text());
      }
    } catch (err) {
      console.error("Failed to fetch user profile", err);
    }
  };

  const fetchSessions = async (token: string) => {
    try {
      const res = await fetch("/api/sessions", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  const loadSession = async (sessionId: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setCurrentSessionId(sessionId);
    setIsMobileSidebarOpen(false); // Close mobile drawer

    try {
      const res = await fetch(`/api/sessions/${sessionId}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const history = data.messages || [];
        const uiMessages = history.map((msg: any) => {
          let content = msg.content;
          if (msg.role === 'assistant') {
            // Assistant messages are stored as full result objects
            if (typeof content === 'object' && content !== null) {
              content = formatResponse(content);
            } else if (typeof content === 'string') {
              try {
                // Try parsing if it's a JSON string
                const parsed = JSON.parse(content);
                content = formatResponse(parsed);
              } catch (e) {
                // Plain text - render as markdown
                content = (
                  <div className="prose prose-stone max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0 text-stone-700 leading-relaxed">{children}</p>,
                        h1: ({ children }) => <h1 className="text-2xl font-bold text-stone-800 mb-3">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-xl font-bold text-stone-800 mb-2">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-lg font-semibold text-stone-800 mb-2">{children}</h3>,
                        strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
                        ul: ({ children }) => <ul className="list-disc list-inside space-y-1 ml-4">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 ml-4">{children}</ol>,
                        li: ({ children }) => <li className="text-stone-700">{children}</li>,
                        code: ({ children }) => <code className="bg-stone-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
                      }}
                    >
                      {content}
                    </ReactMarkdown>
                  </div>
                );
              }
            }
          }
          return { role: msg.role, content, rawContent: msg.content };
        });
        setMessages(uiMessages);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const createNewSession = () => {
    setMessages([{
      role: 'assistant',
      content: (
        <div className="space-y-2">
          <p className="text-xl font-serif text-primary font-bold">Namaste! 🙏</p>
          <p className="text-stone-600">I am DeepShiva, your holistic health companion. How can I support your well-being today?</p>
        </div>


      )
    }]);
    setCurrentSessionId(null);
    setIsMobileSidebarOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  const handleSubmit = async (overrideInput?: string, generateAudio?: boolean) => {
    const textToSend = overrideInput || input.trim();
    if (!textToSend || isLoading) return;

    const userMessage: Message = { role: 'user', content: textToSend, rawContent: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInput('');

    // Abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const token = localStorage.getItem("token");

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: textToSend,
          session_id: currentSessionId,
          generate_audio: generateAudio,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) throw new Error('Network response error');

      const data = await response.json();

      // Update session ID if new session was created
      if (data.session_id) {
        if (!currentSessionId) {
          // New session created - update state and refresh sessions list
          setCurrentSessionId(data.session_id);
          fetchSessions(token!);
        }
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: formatResponse(data),
        rawContent: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
        audioUrl: data.audio_url
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        audio.play().catch(console.error);
      }

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: 'I apologize, but I am having trouble connecting right now. Please try again.',
          rawContent: 'Error occurred.'
        }]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // --- Audio Player Logic ---
  const playResponse = async (text: string, index: number) => {
    if (playingMessageIndex === index && audioRef.current) {
      if (audioRef.current.paused) {
        audioRef.current.play();
        setIsAudioPlaying(true);
      } else {
        audioRef.current.pause();
        setIsAudioPlaying(false);
      }
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingMessageIndex(null);
      setIsAudioPlaying(false);
    }

    const token = localStorage.getItem("token");
    setIsAudioLoading(index);

    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ text })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audioRef.current = audio;
          audio.onended = () => {
            setPlayingMessageIndex(null);
            setIsAudioPlaying(false);
          };
          audio.play();
          setPlayingMessageIndex(index);
          setIsAudioPlaying(true);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsAudioLoading(null);
    }
  };

  // --- Render ---
  return (
    <div className="flex h-screen bg-[#FDFCF8] text-stone-800 overflow-hidden font-sans">

      {/* Mobile Sidebar Overlay */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`
          fixed md:relative z-50 h-full flex-shrink-0 bg-[#3A5A40] text-stone-100 transition-all duration-300 ease-in-out shadow-xl
          ${isMobileSidebarOpen ? 'translate-x-0 w-72' : '-translate-x-full md:translate-x-0'}
          ${isSidebarOpen ? 'md:w-72' : 'md:w-[0px] md:overflow-hidden'}
        `}
      >
        <div className="flex flex-col h-full w-72"> {/* Fixed width inner container prevents content squishing */}

          {/* Sidebar Header */}
          <div className="p-6 flex items-center justify-between border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="bg-white/10 p-2 rounded-lg">
                <Leaf className="w-5 h-5 text-emerald-200" />
              </div>
              <span className="font-serif font-bold text-xl text-[#F2E8CF]">DeepShiva</span>
            </div>
            <button onClick={() => setIsMobileSidebarOpen(false)} className="md:hidden text-white/70 hover:text-white">
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* New Chat Button */}
          <div className="p-4">
            <button
              onClick={createNewSession}
              className="w-full flex items-center justify-center gap-2 bg-[#F2E8CF] hover:bg-white text-[#3A5A40] px-4 py-3 rounded-xl transition-all shadow-md hover:shadow-lg font-bold"
            >
              <Plus className="w-5 h-5" />
              <span>New Consultation</span>
            </button>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2 scrollbar-thin scrollbar-thumb-white/20">
            <h3 className="text-xs font-semibold text-emerald-200/70 uppercase tracking-widest mb-2 px-2">History</h3>
            {(Array.isArray(sessions) ? sessions : []).map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 transition-all border border-transparent
                  ${currentSessionId === session.id
                    ? 'bg-white/10 text-white border-white/10 shadow-sm'
                    : 'text-stone-300 hover:bg-white/5 hover:text-white'
                  }`}
              >
                <MessageCircle className="w-4 h-4 shrink-0 opacity-70" />
                <span className="truncate">{session.title}</span>
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 bg-[#334f38] space-y-2">

            {/* NEW: Profile Button */}
            <button
              onClick={() => router.push('/profile')}
              className="w-full flex items-center gap-3 text-stone-300 hover:text-white hover:bg-white/10 px-4 py-3 rounded-lg transition-colors text-sm font-medium"
            >
              <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                <User className="w-3 h-3" />
              </div>
              My Profile
            </button>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 text-stone-300 hover:text-red-300 hover:bg-red-500/10 px-4 py-3 rounded-lg transition-colors text-sm font-medium"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full relative w-full">

        {/* Top Navbar */}
        <header className="bg-white border-b border-stone-200 h-16 flex items-center px-4 justify-between shadow-sm z-10">
          <div className="flex items-center gap-3">
            {/* Sidebar Toggles */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="md:hidden p-2 text-stone-600 hover:bg-stone-100 rounded-lg"
            >
              <Menu className="w-6 h-6" />
            </button>

            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="hidden md:flex p-2 text-stone-500 hover:text-[#3A5A40] hover:bg-stone-100 rounded-lg transition-colors"
            >
              {isSidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>

            <div>
              <h1 className="font-serif font-bold text-stone-800 text-lg">Holistic Assistant</h1>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs text-stone-500 font-medium">Ayurveda & Yoga Intelligence</span>
              </div>
            </div>
          </div>

          {/* User Profile - Right Side */}
          {userProfile && (
            <div className="flex items-center gap-2">
              {userProfile.photo_url ? (
                <Image
                  src={userProfile.photo_url}
                  alt={userProfile.display_name || 'User'}
                  width={36}
                  height={36}
                  className="rounded-full border-2 border-[#3A5A40]/20 shadow-sm"
                  onError={(e) => {
                    console.error('Failed to load header avatar:', userProfile.photo_url);
                  }}
                />
              ) : (
                <div className="w-9 h-9 rounded-full bg-[#3A5A40] flex items-center justify-center text-white text-sm font-bold shadow-sm">
                  {(userProfile.display_name || userProfile.email).charAt(0).toUpperCase()}
                </div>
              )}
              <span className="hidden sm:block text-sm font-medium text-stone-700">
                {userProfile.display_name || userProfile.email.split('@')[0]}
              </span>
            </div>
          )}
        </header>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-hidden relative bg-[url('https://www.transparenttextures.com/patterns/cream-paper.png')]">
          {/* Optional: You can remove the bg-url if you prefer plain color, or add a subtle pattern */}

          <div className="h-full max-w-4xl mx-auto px-4 md:px-8 py-6 overflow-y-auto scrollbar-thin">

            {/* Empty State */}
            {messages.length === 0 && !currentSessionId && (
              <div className="flex flex-col items-center justify-center h-[80%] text-center space-y-6 animate-in fade-in duration-700">
                <div className="w-24 h-24 bg-[#E0E5D9] rounded-full flex items-center justify-center mb-4 shadow-inner">
                  <Leaf className="w-12 h-12 text-[#3A5A40]" />
                </div>
                <div>
                  <h2 className="text-3xl font-serif font-bold text-[#3A5A40] mb-2">Swastha</h2>
                  <p className="text-stone-500 max-w-md mx-auto">
                    "Health is not just the absence of disease, but the balance of mind, body, and spirit."
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full mt-8">
                  {["Remedies for migraine?", "Yoga for back pain", "Pitt dosha diet", "Meditation for sleep"].map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSubmit(q)}
                      className="text-sm bg-white border border-stone-200 p-3 rounded-xl hover:border-[#3A5A40] hover:text-[#3A5A40] hover:shadow-md transition-all text-stone-600"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message List */}
            <div className="space-y-8 pb-4">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

                  <div className={`flex gap-4 max-w-[90%] md:max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>

                    {/* Avatar */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm border
                      ${msg.role === 'assistant'
                        ? 'bg-[#E0E5D9] border-[#3A5A40]/20'
                        : 'bg-[#3A5A40] border-[#3A5A40]'
                      }`}

                    >
                      {msg.role === 'assistant' ? (
                        <Leaf className="w-5 h-5 text-[#3A5A40]" />
                      ) : userProfile?.photo_url ? (
                        <Image
                          src={userProfile.photo_url}
                          alt={userProfile.display_name || 'User'}
                          width={40}
                          height={40}
                          className="rounded-full object-cover"
                          onError={(e) => {
                            // Fallback if image fails to load
                            console.error('Failed to load user avatar:', userProfile.photo_url);
                          }}
                        />
                      ) : null}
                      {/* Fallback avatar (shown if image fails) */}
                      {msg.role !== 'assistant' && (
                        <span className={`text-white font-bold text-sm ${userProfile?.photo_url ? 'hidden' : ''}`}>
                          {userProfile?.display_name?.[0]?.toUpperCase() || userProfile?.email?.[0]?.toUpperCase() || 'U'}
                        </span>
                      )}
                    </div>

                    {/* Bubble */}
                    <div className={`
                      rounded-2xl p-5 shadow-sm relative group transition-all
                      ${msg.role === 'user'
                        ? 'bg-[#3A5A40] text-white rounded-tr-none' // User Bubble
                        : 'bg-white text-stone-800 border border-stone-100 rounded-tl-none hover:shadow-organic' // Bot Bubble
                      }
                    `}>
                      <div className="text-[15px] leading-7">
                        {msg.content}
                      </div>

                      {/* Audio Controls for Bot */}
                      {msg.role === 'assistant' && (
                        <div className="mt-4 pt-3 border-t border-stone-100 flex items-center gap-3">
                          <button
                            onClick={() => {
                              const contentToRead = msg.rawContent || "No content available";
                              playResponse(contentToRead, index);
                            }}
                            disabled={isAudioLoading === index}
                            className={`
                              flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all border
                              ${playingMessageIndex === index
                                ? "bg-[#3A5A40] text-white border-[#3A5A40]"
                                : "bg-stone-50 text-stone-600 border-stone-200 hover:border-[#3A5A40] hover:text-[#3A5A40]"
                              }
                            `}
                          >
                            {isAudioLoading === index ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : playingMessageIndex === index && isAudioPlaying ? (
                              <Pause className="w-3 h-3" />
                            ) : (
                              <Play className="w-3 h-3" />
                            )}
                            {playingMessageIndex === index && isAudioPlaying ? "Pause Voice" : "Listen"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-4 max-w-[80%]">
                    <div className="w-10 h-10 rounded-full bg-[#E0E5D9] flex items-center justify-center shrink-0">
                      <Leaf className="w-5 h-5 text-[#3A5A40]" />
                    </div>
                    <div className="bg-white p-4 rounded-2xl rounded-tl-none border border-stone-100 shadow-sm flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin text-[#3A5A40]" />
                      <span className="text-stone-500 text-sm font-medium">Consulting Ayurvedic Knowledge Base...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-stone-200 px-4 py-5 pb-6">
          <div className="max-w-4xl mx-auto flex items-end gap-3">

            <div className="relative flex-1 group">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                className="w-full pl-6 pr-4 py-4 rounded-2xl bg-stone-50 border border-stone-200 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] text-stone-800 placeholder:text-stone-400 transition-all shadow-inner"
                placeholder="Ask about symptoms, doshas, or yoga..."
                disabled={isLoading}
              />
            </div>

            <div className="flex items-center gap-2">
              <VoiceRecorder
                onTranscribed={(text) => handleSubmit(text, true)}
                onError={console.error}
              />

              <button
                onClick={() => handleSubmit()}
                disabled={isLoading || !input.trim()}
                className="p-4 bg-[#3A5A40] hover:bg-[#2F4A33] text-white rounded-full transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:shadow-none hover:-translate-y-1 active:translate-y-0"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </div>
          <p className="text-center text-[11px] text-stone-400 mt-3 font-medium">
            Ayurveda supports, it does not replace. In emergencies, seek professional medical help immediately.
          </p>
        </div>
      </main>
    </div>
  );
}