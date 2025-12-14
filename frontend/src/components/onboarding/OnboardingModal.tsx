"use client";

import { useState, useEffect } from "react";
import { X, ChevronRight, ChevronLeft, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// Define the shape of our form data
interface OnboardingData {
  age: string;
  gender: string;
  existingConditions: string;
  medications: string;
  previousConditions: string;
  address: {
    street: string;
    district: string;
    state: string;
    pincode: string;
  };
}

const INITIAL_DATA: OnboardingData = {
  age: "",
  gender: "",
  existingConditions: "",
  medications: "",
  previousConditions: "",
  address: { street: "", district: "", state: "", pincode: "" },
};

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (data: OnboardingData) => Promise<void>;
}

export default function OnboardingModal({ isOpen, onClose, onComplete }: OnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<OnboardingData>(INITIAL_DATA);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Configuration for each slide
  const slides = [
    {
      id: "age",
      question: "How old are you?",
      subtext: "This helps us tailor health advice appropriate for your life stage.",
      type: "number",
      field: "age",
      placeholder: "e.g. 25",
    },
    {
      id: "gender",
      question: "What is your gender?",
      subtext: "Biological factors influence Ayurvedic constitution (Prakriti).",
      type: "options",
      field: "gender",
      options: ["Male", "Female", "Other", "Prefer not to say"],
    },
    {
      id: "existingConditions",
      question: "Do you have any existing health conditions?",
      subtext: "e.g., Diabetes, Hypertension, Asthma (or leave blank if none)",
      type: "textarea",
      field: "existingConditions",
      placeholder: "List any chronic conditions...",
    },
    {
      id: "medications",
      question: "Are you currently taking any medications?",
      subtext: "This prevents potential interactions with herbal remedies.",
      type: "textarea",
      field: "medications",
      placeholder: "List current prescriptions...",
    },
    {
      id: "previousConditions",
      question: "Any significant past medical history?",
      subtext: "Surgeries, major illnesses, or recovered conditions.",
      type: "textarea",
      field: "previousConditions",
      placeholder: "List past history...",
    },
    {
      id: "address",
      question: "Where are you located?",
      subtext: "We use this to find the nearest hospitals and government schemes.",
      type: "address_group",
      field: "address",
    },
  ];

  // Prevent scrolling when modal is open
  useEffect(() => {
    if (isOpen) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "unset";
    return () => { document.body.style.overflow = "unset"; };
  }, [isOpen]);

  const handleNext = async () => {
    if (currentStep < slides.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // Final Step - Submit
      setIsSubmitting(true);
      try {
        await onComplete(formData);
        onClose();
      } catch (error) {
        console.error("Failed to save profile:", error);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleSkip = () => {
    const field = slides[currentStep].field as keyof OnboardingData;
    
    if (field === 'address') {
       setFormData(prev => ({ ...prev, address: { street: "", district: "", state: "", pincode: "" } }));
    } else {
       setFormData(prev => ({ ...prev, [field]: "" }));
    }
    handleNext();
  };

  const updateField = (value: string | object) => {
    const field = slides[currentStep].field as keyof OnboardingData;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Helper to render the correct input based on slide type
  const renderInput = () => {
    const slide = slides[currentStep];

    switch (slide.type) {
      case "number":
      case "text":
        return (
          <input
            type={slide.type}
            value={formData[slide.field as keyof OnboardingData] as string}
            onChange={(e) => updateField(e.target.value)}
            className="w-full bg-stone-50 border-b-2 border-stone-300 focus:border-[#3A5A40] p-4 text-2xl font-serif text-stone-800 outline-none transition-colors placeholder:text-stone-300"
            placeholder={slide.placeholder}
            autoFocus
          />
        );
      case "textarea":
        return (
          <textarea
            value={formData[slide.field as keyof OnboardingData] as string}
            onChange={(e) => updateField(e.target.value)}
            className="w-full h-40 bg-stone-50 border-2 border-stone-200 rounded-xl p-4 text-lg text-stone-800 focus:border-[#3A5A40] outline-none transition-colors resize-none"
            placeholder={slide.placeholder}
            autoFocus
          />
        );
      case "options":
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(slide.options || []).map((opt) => (
              <button
                key={opt}
                onClick={() => updateField(opt)}
                className={`p-6 rounded-xl border-2 text-left transition-all ${
                  formData.gender === opt
                    ? "border-[#3A5A40] bg-[#3A5A40]/10 text-[#3A5A40] font-bold shadow-md"
                    : "border-stone-200 hover:border-[#3A5A40]/50 text-stone-600"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        );
      case "address_group":
        return (
          <div className="space-y-4">
            <input
              placeholder="Street Address"
              value={formData.address.street}
              onChange={(e) => setFormData(prev => ({ ...prev, address: { ...prev.address, street: e.target.value } }))}
              className="w-full bg-stone-50 border border-stone-300 rounded-lg p-3 outline-none focus:border-[#3A5A40]"
            />
            <div className="grid grid-cols-2 gap-4">
              <input
                placeholder="District"
                value={formData.address.district}
                onChange={(e) => setFormData(prev => ({ ...prev, address: { ...prev.address, district: e.target.value } }))}
                className="w-full bg-stone-50 border border-stone-300 rounded-lg p-3 outline-none focus:border-[#3A5A40]"
              />
              <input
                placeholder="State"
                value={formData.address.state}
                onChange={(e) => setFormData(prev => ({ ...prev, address: { ...prev.address, state: e.target.value } }))}
                className="w-full bg-stone-50 border border-stone-300 rounded-lg p-3 outline-none focus:border-[#3A5A40]"
              />
            </div>
            <input
              placeholder="Pincode"
              value={formData.address.pincode}
              onChange={(e) => setFormData(prev => ({ ...prev, address: { ...prev.address, pincode: e.target.value } }))}
              className="w-full bg-stone-50 border border-stone-300 rounded-lg p-3 outline-none focus:border-[#3A5A40]"
            />
          </div>
        );
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl bg-[#FDFCF8] rounded-3xl shadow-2xl overflow-hidden flex flex-col min-h-[500px]"
      >
        {/* Progress Bar */}
        <div className="h-2 bg-stone-200 w-full">
          <div 
            className="h-full bg-[#3A5A40] transition-all duration-500 ease-out"
            style={{ width: `${((currentStep + 1) / slides.length) * 100}%` }}
          />
        </div>

        {/* Header */}
        <div className="p-6 flex justify-between items-center text-stone-400">
           <div className="text-sm font-medium tracking-widest uppercase">
             Step {currentStep + 1} of {slides.length}
           </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 px-8 md:px-12 flex flex-col justify-center">
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentStep}
                    initial={{ x: 20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: -20, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                >
                    <h2 className="text-3xl md:text-4xl font-serif font-bold text-stone-800 mb-2">
                        {slides[currentStep].question}
                    </h2>
                    <p className="text-stone-500 mb-8 text-lg">
                        {slides[currentStep].subtext}
                    </p>
                    
                    <div className="mb-8">
                        {renderInput()}
                    </div>
                </motion.div>
            </AnimatePresence>
        </div>

        {/* Footer Actions */}
        <div className="p-8 border-t border-stone-100 flex justify-between items-center bg-white">
            <button 
                onClick={handleSkip}
                className="text-stone-400 hover:text-stone-600 font-medium px-4 py-2 transition-colors text-sm uppercase tracking-wide"
            >
                Skip Question
            </button>

            <button
                onClick={handleNext}
                disabled={isSubmitting}
                className="bg-[#3A5A40] hover:bg-[#2F4A33] text-white px-8 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg hover:shadow-[#3A5A40]/30 hover:-translate-y-1 active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
            >
                {isSubmitting ? "Finishing..." : currentStep === slides.length - 1 ? "Complete Profile" : "Next"}
                {!isSubmitting && <ArrowRight className="w-5 h-5" />}
            </button>
        </div>
      </motion.div>
    </div>
  );
}
