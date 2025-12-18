"use client";
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import {
  Leaf, Send, Sparkles, Loader2, Plus, MessageCircle,
  LogOut, Menu, X, Volume2, Pause, Play, ChevronLeft,
  ChevronRight, Youtube, Activity, User, Bell, FileText, MapPin
} from 'lucide-react';
import VoiceRecorder from "./VoiceRecorder";
import DocumentUploader from "./DocumentUploader";
import { getValidToken, setupTokenRefresh, onAuthChange } from "@/lib/firebase-client";
import HealthAlertsWidget from "./HealthAlertsWidget";
import OnboardingModal from "./onboarding/OnboardingModal";
import { useTranslations, useLocale } from 'next-intl';
import LanguageSwitcher from './LanguageSwitcher';

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

const formatResponse = (response: ChatResponse, t: any): React.ReactNode => {
  const { intent, output, yoga_videos, yoga_recommendations } = response;

  const renderContent = (content: string | { message: string; emergency?: boolean } | unknown) => {
    if (typeof content === 'string') {
      return (
        <div className="prose prose-stone max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-3 text-stone-700 leading-relaxed text-[15px]">{children}</p>,
              h1: ({ children }) => <h1 className="text-2xl font-bold text-stone-800 mb-4 mt-6">{children}</h1>,
              h2: ({ children }) => <h2 className="text-xl font-bold text-stone-800 mb-3 mt-5">{children}</h2>,
              h3: ({ children }) => <h3 className="text-lg font-semibold text-stone-800 mb-3 mt-4">{children}</h3>,
              strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
              ul: ({ children }) => <ul className="list-disc ml-5 space-y-0.5 my-2">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal ml-5 space-y-0.5 my-2">{children}</ol>,
              li: ({ children }) => <li className="text-stone-700 text-[15px] leading-relaxed">{children}</li>,
              code: ({ children }) => <code className="bg-stone-100 px-1.5 py-0.5 rounded text-sm font-mono text-stone-800">{children}</code>,
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
              <p className="font-semibold text-sm">{t('emergencyWarning')} {msgContent.emergency}</p>
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
            {t('yogaRecommendations')}
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
            {t('curatedVideos')}
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
                      {t('watch')}
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
  const locale = useLocale(); // Get current locale (en or hi)

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [pendingRequests, setPendingRequests] = useState<Set<string>>(new Set()); // Track sessions with pending requests
  const [showPendingWarning, setShowPendingWarning] = useState(false);
  const [userProfile, setUserProfile] = useState<{
    email: string;
    display_name?: string;
    photo_url?: string;
  } | null>(null);

  // Translations
  const t = useTranslations('Chat');
  const tNav = useTranslations('Navigation');
  const tHead = useTranslations('Header');
  const tAlerts = useTranslations('Alerts');

  // File Upload State
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLocating, setIsLocating] = useState(false); // Emergency Locator State
  const [isProcessingAudio, setIsProcessingAudio] = useState(false); // STT processing state
  // UI State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Desktop default open
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false); // Health Alerts
  const [showOnboarding, setShowOnboarding] = useState(false); // Onboarding modal
  const [showDocumentUpload, setShowDocumentUpload] = useState(false); // Document upload modal

  // Audio State
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isAudioLoading, setIsAudioLoading] = useState<number | null>(null);

  // Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeRequestsRef = useRef<Map<string, AbortController>>(new Map()); // Track active requests per session
  const sessionMessagesRef = useRef<Map<string, Message[]>>(new Map()); // Store messages per session
  const sessionLoadAbortRef = useRef<AbortController | null>(null);
  const isLoadingSessionRef = useRef<boolean>(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // --- Effects ---
  useEffect(() => {
    // Setup Firebase auth listener
    const unsubscribe = onAuthChange(async (user) => {
      if (!user) {
        console.log("⚠️ No Firebase user - redirecting to login");
        router.push("/login");
        return;
      }

      // Get fresh token
      const token = await getValidToken();
      if (token) {
        fetchSessions(token);
        fetchUserProfile(token);
      }
    });

    // Setup automatic token refresh every 50 minutes
    setupTokenRefresh();

    // Auto-collapse sidebar on small screens
    const handleResize = () => {
      if (window.innerWidth < 768) setIsSidebarOpen(false);
      else setIsSidebarOpen(true);
    };

    handleResize(); // Initial check
    window.addEventListener('resize', handleResize);

    return () => {
      unsubscribe();
      window.removeEventListener('resize', handleResize);
    };
  }, [router]);


  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // --- API Functions ---
  const fetchUserProfile = async (token?: string) => {
    const validToken = token || await getValidToken();
    if (!validToken) return;

    try {
      const res = await fetch(`/api/auth/me`, {
        headers: { Authorization: `Bearer ${validToken}` }
      });
      if (res.ok) {
        const profile = await res.json();
        console.log("User profile loaded:", profile);
        setUserProfile(profile);

        // Check if profile is incomplete (trigger onboarding)
        const isAgeMissing =
          profile.age === null ||
          profile.age === undefined ||
          profile.age === 0 ||
          profile.age === "0" ||
          profile.age === "";

        const isGenderMissing =
          !profile.gender ||
          profile.gender === "" ||
          profile.gender === "Unknown" ||
          profile.gender === null;

        if (isAgeMissing || isGenderMissing) {
          console.log("Profile incomplete. Showing onboarding modal.");
          setShowOnboarding(true);
        }
      } else {
        console.error("Failed to fetch profile:", res.status, await res.text());
      }
    } catch (err) {
      console.error("Failed to fetch user profile", err);
    }
  };

  const fetchSessions = async (token?: string) => {
    const validToken = token || await getValidToken();
    if (!validToken) return;

    try {
      const res = await fetch("/api/sessions", {
        headers: { Authorization: `Bearer ${validToken}` }
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
    const token = await getValidToken();
    if (!token) return;

    // If already on this session, do nothing
    if (currentSessionId === sessionId) {
      console.log(`Already on session ${sessionId}, skipping`);
      return;
    }

    console.log(`Loading session: ${sessionId}`);

    // Save current session messages before switching
    if (currentSessionId) {
      console.log(`Saving messages for session: ${currentSessionId}`);
      sessionMessagesRef.current.set(currentSessionId, messages);
    }

    // Prevent concurrent session loads
    if (isLoadingSessionRef.current) {
      console.log('Session load already in progress, aborting previous...');
      // Abort the previous load and continue with this one
      if (sessionLoadAbortRef.current) {
        sessionLoadAbortRef.current.abort();
        sessionLoadAbortRef.current = null;
      }
    }

    isLoadingSessionRef.current = true;
    const previousSessionId = currentSessionId;
    setCurrentSessionId(sessionId);
    setIsMobileSidebarOpen(false);

    // Check if session has cached messages (but skip if coming from same session)
    const cachedMessages = sessionMessagesRef.current.get(sessionId);
    if (cachedMessages && cachedMessages.length > 0 && previousSessionId !== sessionId) {
      console.log(`Using cached messages for session: ${sessionId}`);
      setMessages(cachedMessages);
      setIsLoading(pendingRequests.has(sessionId));
      setShowPendingWarning(pendingRequests.has(sessionId));
      isLoadingSessionRef.current = false;
      return;
    }

    console.log(`Fetching history for session: ${sessionId}`);
    const abortController = new AbortController();
    sessionLoadAbortRef.current = abortController;

    try {
      const res = await fetch(`/api/sessions/${sessionId}/history`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortController.signal,
      });
      if (res.ok) {
        const data = await res.json();
        const history = data.messages || [];
        const uiMessages = history.map((msg: any) => {
          let content = msg.content;
          if (msg.role === 'assistant') {
            // Assistant messages are stored as full result objects
            if (typeof content === 'object' && content !== null) {
              content = formatResponse(content, t);
            } else if (typeof content === 'string') {
              try {
                // Try parsing if it's a JSON string
                const parsed = JSON.parse(content);
                content = formatResponse(parsed, t);
              } catch (e) {
                // Plain text - render as markdown
                content = (
                  <div className="prose prose-stone max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-3 text-stone-700 leading-relaxed text-[15px]">{children}</p>,
                        h1: ({ children }) => <h1 className="text-2xl font-bold text-stone-800 mb-4 mt-6">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-xl font-bold text-stone-800 mb-3 mt-5">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-lg font-semibold text-stone-800 mb-3 mt-4">{children}</h3>,
                        strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
                        ul: ({ children }) => <ul className="list-disc ml-5 space-y-0.5 my-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal ml-5 space-y-0.5 my-2">{children}</ol>,
                        li: ({ children }) => <li className="text-stone-700 text-[15px] leading-relaxed">{children}</li>,
                        code: ({ children }) => <code className="bg-stone-100 px-1.5 py-0.5 rounded text-sm font-mono text-stone-800">{children}</code>,
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
        console.log(`Loaded ${uiMessages.length} messages for session ${sessionId}`);

        // Always update - currentSessionId is already set to sessionId at this point
        setMessages(uiMessages);
        sessionMessagesRef.current.set(sessionId, uiMessages);
        setIsLoading(pendingRequests.has(sessionId));
        setShowPendingWarning(pendingRequests.has(sessionId));
      } else {
        console.error(`Failed to load session ${sessionId}: ${res.status}`);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error("Failed to load history", err);
      } else {
        console.log('Session load aborted');
      }
    } finally {
      isLoadingSessionRef.current = false;
      if (sessionLoadAbortRef.current === abortController) {
        sessionLoadAbortRef.current = null;
      }
      console.log(`Session load complete for: ${sessionId}`);
    }
  };

  const createNewSession = () => {
    // Save current session messages before creating new one
    if (currentSessionId) {
      sessionMessagesRef.current.set(currentSessionId, messages);
    }

    // Abort any ongoing session loads
    if (sessionLoadAbortRef.current) {
      sessionLoadAbortRef.current.abort();
      sessionLoadAbortRef.current = null;
    }

    // Show warning if there are pending requests
    const hasPendingRequests = pendingRequests.size > 0;
    setShowPendingWarning(hasPendingRequests);

    // Reset loading states for new session
    setIsLoading(false);
    isLoadingSessionRef.current = false;

    setMessages([{
      role: 'assistant',
      content: (
        <div className="space-y-2">
          <p className="text-xl font-serif text-primary font-bold">{t('greetingTitle')}</p>
          <p className="text-stone-600">{t('greetingBody')}</p>
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

    // Clear pending warning when starting new request
    setShowPendingWarning(false);

    // Capture current session ID for this request
    const requestSessionId = currentSessionId;
    const requestKey = requestSessionId || 'new';

    // Track pending request for this session
    const abortController = new AbortController();
    activeRequestsRef.current.set(requestKey, abortController);
    setPendingRequests(prev => new Set(prev).add(requestKey));

    const token = await getValidToken();
    if (!token) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: t('sessionExpired'),
        rawContent: 'Session expired.'
      }]);
      setIsLoading(false);
      return;
    }

    try {
      // Get user's location for emergency services
      let userLocation: { latitude?: number; longitude?: number } = {};
      console.log("🔍 [STEP 1] Attempting to get browser geolocation...");
      try {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            timeout: 5000,
            maximumAge: 60000 // Cache for 1 minute
          });
        });
        userLocation = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        };
        console.log("✅ [STEP 1] Browser location captured:", {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: new Date(position.timestamp).toISOString()
        });
      } catch (geoError) {
        console.error("❌ [STEP 1] Location error:", geoError);
        console.log("   Error name:", (geoError as any).code);
        console.log("   Error message:", (geoError as any).message);
        // Continue without location - non-blocking
      }

      const requestBody = {
        query: textToSend,
        session_id: requestSessionId,
        generate_audio: generateAudio,
        locale: locale,  // Send user's language preference
        ...userLocation  // Include lat/lon if available
      };
      console.log("📤 [STEP 2] Sending request to backend:", {
        endpoint: '/api/chat',
        hasLatitude: 'latitude' in requestBody,
        hasLongitude: 'longitude' in requestBody,
        latitude: requestBody.latitude,
        longitude: requestBody.longitude,
        locale: requestBody.locale
      });
      console.log("📝 [STEP 2.5] Request body object:", requestBody);
      console.log("📝 [STEP 2.6] Stringified JSON:", JSON.stringify(requestBody, null, 2));
      
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody),
        signal: abortController.signal,
      });

      if (!response.ok) throw new Error('Network response error');

      const data = await response.json();
      console.log("📦 [STEP 3] Full API Response:", data);
      console.log("   - Has nearby_hospitals:", 'nearby_hospitals' in data);
      console.log("   - nearby_hospitals value:", data.nearby_hospitals);
      console.log("   - nearby_hospitals type:", typeof data.nearby_hospitals);
      console.log("   - nearby_hospitals length:", Array.isArray(data.nearby_hospitals) ? data.nearby_hospitals.length : 'N/A');
      console.log("🔍 Checking emergency conditions:");
      console.log("  - data.intent:", data.intent);
      console.log("  - data.symptom_assessment:", data.symptom_assessment);
      console.log("  - data.output type:", typeof data.output);

      // Determine final session ID
      const finalSessionId = data.session_id || requestSessionId;

      // Update session ID if new session was created
      if (data.session_id && !requestSessionId) {
        setCurrentSessionId(data.session_id);
        fetchSessions(token!);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: formatResponse(data, t),
        rawContent: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
        audioUrl: data.audio_url
      };

      // Update messages in current view OR cache for other session
      if (currentSessionId === finalSessionId || (!currentSessionId && !requestSessionId)) {
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        // Response arrived for a different session - cache it
        const cachedMessages = sessionMessagesRef.current.get(finalSessionId) || [];
        sessionMessagesRef.current.set(finalSessionId, [...cachedMessages, assistantMessage]);
        console.log(`Response cached for session ${finalSessionId}`);
      }

      if (data.audio_url && currentSessionId === finalSessionId) {
        const audio = new Audio(data.audio_url);
        audio.play().catch(console.error);
      }

      // Check for emergency intent and display hospitals from backend
      const isEmergency =
        data.intent === 'emergency' ||
        (data.symptom_assessment && data.symptom_assessment.is_emergency === true) ||
        (data.output && typeof data.output === 'object' && data.output.emergency);

      if (isEmergency) {
        console.log("🚨 Emergency detected!");
        
        // If backend provided hospitals, display them
        if (data.nearby_hospitals && Array.isArray(data.nearby_hospitals)) {
          console.log(`✅ Backend provided ${data.nearby_hospitals.length} nearby hospitals`);
          displayHospitals(data.nearby_hospitals);
        } else {
          console.log("⚠️ No hospitals in response, triggering manual locator");
          // Fallback: manually trigger hospital locator
          setTimeout(() => handleEmergencyLocator('auto'), 500);
        }
      }

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        // Only show error in current session
        if (currentSessionId === requestSessionId || (!currentSessionId && !requestSessionId)) {
          setMessages((prev) => [...prev, {
            role: 'assistant',
            content: t('errorConnection'),
            rawContent: 'Error occurred.'
          }]);
        }
      }
    } finally {
      // Clean up pending request tracking
      activeRequestsRef.current.delete(requestKey);
      setPendingRequests(prev => {
        const updated = new Set(prev);
        updated.delete(requestKey);
        return updated;
      });

      // Only clear loading if we're still in the same session
      if (currentSessionId === requestSessionId || (!currentSessionId && !requestSessionId)) {
        setIsLoading(false);
      }
    }
  };

  // --- Onboarding Handler ---
  const handleOnboardingComplete = async (data: any) => {
    const token = await getValidToken();
    if (!token) {
      console.error("Cannot save profile: no token");
      return;
    }

    try {
      // Parse data from onboarding form
      const payload = {
        age: parseInt(data.age) || 0,
        gender: data.gender || "",
        medical_history: data.existingConditions
          ? data.existingConditions.split(',').map((s: string) => s.trim()).filter(Boolean)
          : [],
        medications: data.medications
          ? data.medications.split(',').map((s: string) => s.trim()).filter(Boolean)
          : [],
        previous_conditions: data.previousConditions
          ? data.previousConditions.split(',').map((s: string) => s.trim()).filter(Boolean)
          : [],
        address: data.address || {}
      };

      const res = await fetch(`/api/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        console.log("Profile updated successfully");
        setShowOnboarding(false);
        // Refresh profile to get updated data
        await fetchUserProfile(token);
      } else {
        console.error("Failed to update profile:", await res.text());
      }
    } catch (err) {
      console.error("Error updating profile:", err);
    }
  };

  // --- Hospital Display Function ---
  const displayHospitals = (hospitals: any[]) => {
    if (!hospitals || hospitals.length === 0) {
      console.log("No hospitals to display");
      return;
    }

    const HospitalList = (
      <div className="space-y-4 w-full">
        <h3 className="text-xl font-serif font-bold text-red-600 flex items-center gap-2 border-b border-red-100 pb-2">
          <Activity className="w-6 h-6 animate-pulse" />
          Emergency Centers Nearby
        </h3>
        <div className="grid gap-3">
          {hospitals.map((hospital: any, i: number) => (
            <div key={i} className="bg-white p-4 rounded-xl border border-red-100 shadow-sm hover:shadow-md transition-all group">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <h4 className="font-bold text-stone-800 text-lg group-hover:text-red-700 transition-colors">{hospital.hospital_name || hospital.name || "Hospital"}</h4>
                  <p className="text-sm text-stone-600 mt-1 flex items-start gap-1.5">
                    <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5 text-stone-400" />
                    {hospital.address_original || hospital.vicinity || hospital.address || "Address not available"}
                  </p>
                </div>
                {hospital.distance_km ? (
                  <div className="bg-amber-50 text-amber-700 text-xs font-bold px-2 py-1 rounded-full shrink-0">
                    {hospital.distance_km.toFixed(1)} km
                  </div>
                ) : hospital.rating ? (
                  <div className="bg-green-50 text-green-700 text-xs font-bold px-2 py-1 rounded-full shrink-0">
                    {hospital.rating} ★
                  </div>
                ) : null}
              </div>

              <div className="flex gap-3 mt-4 text-sm font-medium">
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent((hospital.hospital_name || "") + ", " + (hospital.address_original || hospital.address || ""))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-sm"
                >
                  <MapPin className="w-4 h-4" />
                  Get Directions
                </a>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-stone-500 mt-2 italic">
          * Please verify availability before visiting. In critical emergencies, call 112 directly.
        </p>
      </div>
    );

    setMessages(prev => [...prev, {
      role: 'assistant',
      content: HospitalList,
      rawContent: JSON.stringify(hospitals)
    }]);
  };

  // --- Emergency Locator ---
  const handleEmergencyLocator = (triggerType: 'manual' | 'auto' = 'manual') => {
    if (!navigator.geolocation) {
      if (triggerType === 'manual') alert("Geolocation is not supported by your browser");
      return;
    }

    setIsLocating(true);

    // User message only if manual
    if (triggerType === 'manual') {
      setMessages(prev => [...prev, {
        role: 'user',
        content: "Find nearest hospitals",
        rawContent: "Find nearest hospitals"
      }]);
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
      const { latitude, longitude } = position.coords;
      setIsLoading(true);

      try {
        const res = await fetch(`https://indian-hospital-locator.onrender.com/hospitals/nearby?latitude=${latitude}&longitude=${longitude}&limit=5`);

        if (!res.ok) throw new Error('Failed to fetch hospitals');

        const data = await res.json();

        // Handle various response structures
        let hospitals = Array.isArray(data) ? data : (data.hospitals || []);

        // ALWAYS recalculate distance using Haversine formula for accuracy
        hospitals = hospitals.map((hospital: any) => {
          if (hospital.latitude && hospital.longitude) {
            // Haversine formula to calculate distance
            const R = 6371; // Radius of the Earth in km
            const dLat = (hospital.latitude - latitude) * Math.PI / 180;
            const dLon = (hospital.longitude - longitude) * Math.PI / 180;
            const a = 
              Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(latitude * Math.PI / 180) * Math.cos(hospital.latitude * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            const distance = R * c;
            return { ...hospital, distance_km: distance };
          }
          // Keep existing distance_km if coordinates not available
          return hospital;
        });

        // Sort hospitals by distance (closest first)
        hospitals.sort((a: any, b: any) => {
          const distA = a.distance_km || 999999;
          const distB = b.distance_km || 999999;
          return distA - distB;
        });

        if (hospitals.length === 0) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: "No hospitals found nearby.",
            rawContent: "No hospitals found."
          }]);
          return;
        }

        const HospitalList = (
          <div className="space-y-4 w-full">
            <h3 className="text-xl font-serif font-bold text-red-600 flex items-center gap-2 border-b border-red-100 pb-2">
              <Activity className="w-6 h-6 animate-pulse" />
              Emergency Centers Nearby
            </h3>
            <div className="grid gap-3">
              {hospitals.map((hospital: any, i: number) => (
                <div key={i} className="bg-white p-4 rounded-xl border border-red-100 shadow-sm hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <h4 className="font-bold text-stone-800 text-lg group-hover:text-red-700 transition-colors">{hospital.hospital_name || hospital.name || "Hospital"}</h4>
                      <p className="text-sm text-stone-600 mt-1 flex items-start gap-1.5">
                        <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5 text-stone-400" />
                        {hospital.address_original || hospital.vicinity || hospital.address || "Address not available"}
                      </p>
                    </div>
                    {hospital.distance_km ? (
                      <div className="bg-amber-50 text-amber-700 text-xs font-bold px-2 py-1 rounded-full shrink-0">
                        {hospital.distance_km.toFixed(1)} km
                      </div>
                    ) : hospital.rating ? (
                      <div className="bg-green-50 text-green-700 text-xs font-bold px-2 py-1 rounded-full shrink-0">
                        {hospital.rating} ★
                      </div>
                    ) : null}
                  </div>

                  <div className="flex gap-3 mt-4 text-sm font-medium">
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent((hospital.hospital_name || "") + ", " + (hospital.address_original || hospital.address || ""))}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-sm"
                    >
                      <MapPin className="w-4 h-4" />
                      Get Directions
                    </a>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-stone-500 mt-2 italic">
              * Please verify availability before visiting. In critical emergencies, call 112 directly.
            </p>
          </div>
        );

        setMessages(prev => [...prev, {
          role: 'assistant',
          content: HospitalList,
          rawContent: JSON.stringify(hospitals)
        }]);

      } catch (err) {
        console.error("Hospital locator error:", err);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "Sorry, I couldn't locate nearby hospitals at the moment. Please call 112 for emergency.",
          rawContent: "Error locating hospitals."
        }]);
      } finally {
        setIsLoading(false);
        setIsLocating(false);
      }
    }, (err) => {
      console.error("Geolocation error:", err);
      alert("Unable to access your location. Please check browser permissions.");
      setIsLocating(false);
    });
  };

  // --- Audio Player Logic ---
  const playResponse = async (text: string, index: number) => {
    if (playingMessageIndex === index) {
      if (isAudioPlaying) {
        audioRef.current?.pause();
        setIsAudioPlaying(false);
      } else {
        // RESUME logic
        if (audioRef.current) {
          audioRef.current.play().catch(console.error);
          setIsAudioPlaying(true);
        }
      }
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingMessageIndex(null);
      setIsAudioPlaying(false);
    }

    const token = await getValidToken();
    if (!token) return;

    setIsAudioLoading(index);

    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          text,
          language_code: locale === 'hi' ? 'hi-IN' : 'en-IN' // Map locale to Sarvam language codes
        })
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
    <div className="flex h-screen bg-[#FDFCF8] text-stone-800 overflow-hidden font-sans relative">

      {/* Health Alerts Widget */}
      <HealthAlertsWidget
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        onAskMore={(alert) => {
          // Construct a rich prompt with full context
          const contextPrompt = t('tellMeMoreNews') + `

` + t('newsPrompt', {
            title: alert.title,
            source: alert.source,
            description: alert.description ? alert.description : '',
            url: alert.url !== '#' ? alert.url : ''
          });

          setInput(contextPrompt);
          // Auto-focus the input field
          setTimeout(() => {
            const inputElement = document.querySelector('textarea[placeholder*="Ask about symptoms"]') as HTMLTextAreaElement;
            if (inputElement) {
              inputElement.focus();
            }
          }, 100);
        }}
      />

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
              <span>{tNav('newConsultation')}</span>
            </button>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2 scrollbar-thin scrollbar-thumb-white/20">
            <h3 className="text-xs font-semibold text-emerald-200/70 uppercase tracking-widest mb-2 px-2">{tNav('history')}</h3>
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
              {tNav('myProfile')}
            </button>

            {/* NEW: Blockchain Audit Button */}
            <button
              onClick={() => router.push('/blockchain')}
              className="w-full flex items-center gap-3 text-stone-300 hover:text-white hover:bg-white/10 px-4 py-3 rounded-lg transition-colors text-sm font-medium"
            >
              <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                🔗
              </div>
              {tNav('blockchainAudit')}
            </button>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 text-stone-300 hover:text-red-300 hover:bg-red-500/10 px-4 py-3 rounded-lg transition-colors text-sm font-medium"
            >
              <LogOut className="w-4 h-4" />
              {tNav('signOut')}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full relative w-full">

        {/* Top Navbar */}
        {/* Top Navbar */}
        <header className="bg-white border-b border-stone-200 h-14 sm:h-16 flex items-center px-3 sm:px-4 justify-between shadow-sm z-10">
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Sidebar Toggles */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="md:hidden p-1.5 sm:p-2 text-stone-600 hover:bg-stone-100 rounded-lg"
            >
              <Menu className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>

            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="hidden md:flex p-2 text-stone-500 hover:text-[#3A5A40] hover:bg-stone-100 rounded-lg transition-colors"
            >
              {isSidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>

            <div>
              <h1 className="font-serif font-bold text-stone-800 text-base sm:text-lg">{tHead('title')}</h1>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs text-stone-500 font-medium hidden sm:inline">{tHead('subtitle')}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            {/* Alerts Toggle */}
            <LanguageSwitcher />
            <button
              onClick={() => setIsAlertsOpen(true)}
              className="relative p-1.5 sm:p-2 text-stone-500 hover:text-red-500 hover:bg-red-50 rounded-full transition-all"
              title={tAlerts('title')}
            >
              <Bell className="w-4 h-4 sm:w-5 sm:h-5" />
              <span className="absolute top-1 right-1 sm:top-1.5 sm:right-2 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
            </button>

            {/* User Profile - Right Side */}
            {userProfile && (
              <div className="flex items-center gap-2">
                {userProfile.photo_url ? (
                  <Image
                    src={userProfile.photo_url}
                    alt={userProfile.display_name || 'User'}
                    width={32}
                    height={32}
                    className="w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 border-[#3A5A40]/20 shadow-sm"
                    onError={(e) => {
                      console.error('Failed to load header avatar:', userProfile.photo_url);
                    }}
                  />
                ) : (
                  <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-[#3A5A40] flex items-center justify-center text-white text-xs sm:text-sm font-bold shadow-sm">
                    {(userProfile.display_name || userProfile.email).charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="hidden sm:block text-sm font-medium text-stone-700">
                  {userProfile.display_name || userProfile.email.split('@')[0]}
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-hidden relative bg-[url('https://www.transparenttextures.com/patterns/cream-paper.png')]">
          {/* Optional: You can remove the bg-url if you prefer plain color, or add a subtle pattern */}

          <div className="h-full max-w-4xl mx-auto px-4 md:px-8 py-6 overflow-y-auto scrollbar-thin">

            {/* Pending Request Warning */}
            {showPendingWarning && pendingRequests.size > 0 && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3 text-amber-800 animate-in fade-in duration-300">
                <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-sm">{t('previousResponseLoading')}</p>
                  <p className="text-xs text-amber-700">
                    {t('conversationsProcessing', { count: pendingRequests.size })}
                  </p>
                </div>
                <button
                  onClick={() => setShowPendingWarning(false)}
                  className="text-amber-600 hover:text-amber-800 transition-colors"
                  aria-label="Dismiss warning"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Empty State */}
            {
              messages.length === 0 && !currentSessionId && (
                <div className="flex flex-col items-center justify-center h-[80%] text-center space-y-6 animate-in fade-in duration-700">
                  <div className="w-24 h-24 bg-[#E0E5D9] rounded-full flex items-center justify-center mb-4 shadow-inner">
                    <Leaf className="w-12 h-12 text-[#3A5A40]" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-serif font-bold text-[#3A5A40] mb-2">{t('swastha')}</h2>
                    <p className="text-stone-500 max-w-md mx-auto">
                      {t('healthQuote')}
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full mt-8">
                    {[t('migraineRemedy'), t('backPainYoga'), t('pittDoshaDiet'), t('sleepMeditation')].map((q, i) => (
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
              )
            }

            {/* Message List */}
            <div className="space-y-8 pb-4">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

                  <div className={`flex gap-2 sm:gap-4 max-w-[95%] sm:max-w-[90%] md:max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>

                    {/* Avatar */}
                    <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm border
                      ${msg.role === 'assistant'
                        ? 'bg-[#E0E5D9] border-[#3A5A40]/20'
                        : 'bg-[#3A5A40] border-[#3A5A40]'
                      }`}

                    >
                      {msg.role === 'assistant' ? (
                        <Leaf className="w-4 h-4 sm:w-5 sm:h-5 text-[#3A5A40]" />
                      ) : userProfile?.photo_url ? (
                        <Image
                          src={userProfile.photo_url}
                          alt={userProfile.display_name || 'User'}
                          width={32}
                          height={32}
                          className="w-8 h-8 sm:w-10 sm:h-10 rounded-full object-cover"
                          onError={(e) => {
                            // Fallback if image fails to load
                            console.error('Failed to load user avatar:', userProfile.photo_url);
                          }}
                        />
                      ) : null}
                      {/* Fallback avatar (shown if image fails) */}
                      {msg.role !== 'assistant' && (
                        <span className={`text-white font-bold text-xs sm:text-sm ${userProfile?.photo_url ? 'hidden' : ''}`}>
                          {userProfile?.display_name?.[0]?.toUpperCase() || userProfile?.email?.[0]?.toUpperCase() || 'U'}
                        </span>
                      )}
                    </div>

                    {/* Bubble */}
                    <div className={`
                      rounded-2xl p-3 sm:p-5 shadow-sm relative group transition-all
                      ${msg.role === 'user'
                        ? 'bg-[#3A5A40] text-white rounded-tr-none' // User Bubble
                        : 'bg-white text-stone-800 border border-stone-100 rounded-tl-none hover:shadow-organic' // Bot Bubble
                      }
                    `}>
                      <div className="text-sm sm:text-[15px] leading-6 sm:leading-7">
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
                            {playingMessageIndex === index && isAudioPlaying ? t('pauseVoice') : t('listen')}
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
                      <span className="text-stone-500 text-sm font-medium">{t('consultingKnowledgeBase')}</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div >
        </div >

        {/* Input Area */}
        <div className="bg-white border-t border-stone-200 px-3 sm:px-4 py-3 sm:py-5 pb-4 sm:pb-6">
          <div className="max-w-4xl mx-auto flex items-end gap-2 sm:gap-3">

            <div className="relative flex-1 group">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                className="w-full pl-4 sm:pl-6 pr-4 py-3 sm:py-4 rounded-2xl bg-stone-50 border border-stone-200 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] text-stone-800 placeholder:text-stone-400 transition-all shadow-inner text-sm sm:text-base"
                placeholder={t('askPlaceholder')}
                disabled={isLoading}
              />
            </div>

            <div className="flex items-center gap-1.5 sm:gap-2">
              <button
                onClick={() => setShowDocumentUpload(true)}
                className="p-3 sm:p-4 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-full transition-all shadow-md hover:shadow-lg active:scale-95"
                title="Upload medical document"
              >
                <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>

              <VoiceRecorder
                onTranscribed={(text) => handleSubmit(text, true)}
                onError={console.error}
                onProcessingChange={setIsProcessingAudio}
              />

              <button
                onClick={() => handleEmergencyLocator('manual')}
                disabled={isLocating || isLoading}
                className={`p-3 sm:p-4 rounded-full transition-all shadow-md active:scale-95 disabled:opacity-50
                  ${isLocating ? 'bg-red-100 text-red-400' : 'bg-red-50 hover:bg-red-100 text-red-600'}
                `}
                title="Find Nearby Hospitals (Emergency)"
              >
                {isLocating ? <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" /> : <Activity className="w-4 h-4 sm:w-5 sm:h-5" />}
              </button>

              <button
                onClick={() => handleSubmit()}
                disabled={isLoading || !input.trim() || isProcessingAudio}
                className="p-3 sm:p-4 bg-[#3A5A40] hover:bg-[#2F4A33] text-white rounded-full transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:shadow-none active:scale-95"
              >
                {isLoading ? <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" /> : <Send className="w-4 h-4 sm:w-5 sm:h-5" />}
              </button>
            </div>
            
            {/* Audio Processing Indicator */}
            {isProcessingAudio && (
              <div className="px-4 pb-2">
                <div className="flex items-center gap-2 text-sm text-stone-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing audio...</span>
                </div>
              </div>
            )}
          </div>
          <p className="text-center text-[11px] text-stone-400 mt-3 font-medium">
            {t('disclaimer')}
          </p>
        </div >
      </main >

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={handleOnboardingComplete}
      />

      {/* Document Upload Modal */}
      {showDocumentUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-stone-200 px-6 py-4 flex items-center justify-between rounded-t-2xl">
              <h2 className="text-xl font-serif font-bold text-stone-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                Medical Documents
              </h2>
              <button
                onClick={() => setShowDocumentUpload(false)}
                className="text-stone-400 hover:text-stone-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <DocumentUploader />
            </div>
          </div>
        </div>
      )}
    </div >
  );
}