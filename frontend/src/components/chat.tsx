"use client";
import { useState, useRef, useEffect } from 'react';
import { Heart, Send, Sparkles, Activity, Loader2 } from 'lucide-react';

type Message = {
  role: 'user' | 'assistant';
  content: string | React.ReactNode;
};

type HistoryItem = {
  query: string;
  intent: string;
};

const formatResponse = (response: any): React.ReactNode => {
  const { intent, reasoning, output, yoga_recommendations } = response;

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
    return <pre className="text-sm">{JSON.stringify(content, null, 2)}</pre>;
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
    </div>
  );
};

export default function HealthcareChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: (
        <div className="space-y-3">
          <p className="text-lg">👋 Welcome to your Healthcare Assistant!</p>
          <p className="text-gray-300">I can help you with:</p>
          <ul className="text-sm text-gray-300 space-y-1 ml-4">
            <li>• Government health schemes & eligibility</li>
            <li>• Ayurvedic remedies & wellness advice</li>
            <li>• Symptom assessment & guidance</li>
            <li>• Yoga recommendations for various conditions</li>
          </ul>
          <p className="text-sm text-amber-400/80 mt-3">💡 How can I assist you today?</p>
        </div>
      )
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInput('');

    const history: HistoryItem[] = messages
      .filter((msg) => msg.role === 'user')
      .map((msg) => ({ query: msg.content as string, intent: 'unknown' }));

    // Simulate API call with mock response
    // setTimeout(() => {
    //   const mockResponse = {
    //     intent: 'general_query',
    //     output: `This is a simulated response for: "${input}"\n\nIn your actual implementation, this would connect to your backend API at /api/chat with the full healthcare logic.`
    //   };
      
    //   const assistantMessage: Message = {
    //     role: 'assistant',
    //     content: formatResponse(mockResponse),
    //   };
    //   setMessages((prev) => [...prev, assistantMessage]);
    //   setIsLoading(false);
    // }, 1000);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input, history }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
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
    <div className="flex flex-col h-screen from-slate-900 via-blue-950 to-slate-900 overflow-hidden">
      {/* Header */}
      <header className="bg-white/5 backdrop-blur-xl border-b border-white/10 px-6 py-4 shadow-xl">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 from-emerald-400 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg">
              <Heart className="w-6 h-6 text-white" fill="white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Healthcare Assistant</h1>
              <p className="text-xs text-emerald-300 flex items-center gap-1">
                <Activity className="w-3 h-3" />
                AI-Powered Health Support
              </p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-400 bg-white/5 px-3 py-1.5 rounded-full">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            Online
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto px-4 py-6 overflow-y-auto">
          <div className="space-y-6 pb-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
              >
                <div className="flex gap-3 max-w-[85%]">
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 from-emerald-400 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg">
                      <Heart className="w-4 h-4 text-white" fill="white" />
                    </div>
                  )}
                  <div
                    className={`rounded-2xl p-4 shadow-lg ${
                      msg.role === 'user'
                        ? 'from-blue-500 to-cyan-500 text-white ml-auto'
                        : 'bg-white/10 backdrop-blur-xl text-gray-100 border border-white/10'
                    }`}
                  >
                    <div className="text-sm leading-relaxed">{msg.content}</div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg">
                      <span className="text-white font-semibold text-sm">You</span>
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
                      <span className="text-sm">Analyzing your query...</span>
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
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-end">
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
            <button
              onClick={handleSubmit}
              className="px-6 py-3.5 from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white rounded-2xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg hover:shadow-emerald-500/25"
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">
            This assistant provides general information. Always consult healthcare professionals for medical advice.
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.4s ease-out;
        }
      `}</style>
    </div>
  );
}