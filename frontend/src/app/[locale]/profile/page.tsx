"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  User, Mail, Phone, ArrowLeft, Save, Edit2,
  Leaf, Loader2, Camera, Calendar, Users, Pill, Heart, MapPin
} from "lucide-react";
import { useTranslations } from 'next-intl';
import LanguageSwitcher from "@/components/LanguageSwitcher";

type UserProfile = {
  name: string;
  email: string;
  phone?: string;
  age?: number;
  gender?: string;
  medical_history?: string[];
  medications?: string[];
  previous_conditions?: string[];
  address?: {
    street?: string;
    district?: string;
    state?: string;
    pincode?: string;
  };
};

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile>({
    name: "",
    email: "",
    phone: "",
    age: 0,
    gender: "",
    medical_history: [],
    medications: [],
    previous_conditions: [],
    address: {}
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const t = useTranslations('Profile');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        console.log("Profile data:", data); // Debug log
        setProfile({
          name: data.display_name || "",
          email: data.email || "",
          phone: data.phone || "",
          age: data.age || 0,
          gender: data.gender || "",
          medical_history: data.medical_history || [],
          medications: data.medications || [],
          previous_conditions: data.previous_conditions || [],
          address: data.address || {}
        });
      } else {
        const errorText = await res.text();
        console.error("Profile fetch failed:", res.status, errorText);
        setError(`Failed to load profile: ${res.status}`);
      }
    } catch (err) {
      console.error("Failed to load profile", err);
      setError("Failed to load profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    const token = localStorage.getItem("token");

    try {
      // Convert string fields to arrays before sending
      const payload = {
        ...profile,
        medical_history: typeof (profile.medical_history as any) === 'string'
          ? (profile.medical_history as any).split(',').map((s: string) => s.trim()).filter(Boolean)
          : profile.medical_history,
        medications: typeof (profile.medications as any) === 'string'
          ? (profile.medications as any).split(',').map((s: string) => s.trim()).filter(Boolean)
          : profile.medications,
        previous_conditions: typeof (profile.previous_conditions as any) === 'string'
          ? (profile.previous_conditions as any).split(',').map((s: string) => s.trim()).filter(Boolean)
          : profile.previous_conditions
      };

      const res = await fetch('/api/profile', {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to update profile");

      setSuccess(t('successUpdate'));
      setIsEditing(false);
      // Refresh profile to get updated data
      await fetchProfile();
    } catch (err) {
      console.error("Profile update error:", err);
      setError("Failed to update profile. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FDFCF8] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#3A5A40] animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFCF8] font-sans">
      {/* Navbar / Header */}
      <header className="bg-white border-b border-stone-200 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 text-stone-500 hover:text-[#3A5A40] hover:bg-stone-50 rounded-full transition-colors"
            >
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-xl font-serif font-bold text-stone-800">{t('title')}</h1>
          </div>
          <LanguageSwitcher />
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-4 md:p-8">

        {/* Profile Header Card */}
        <div className="bg-gradient-to-br from-[#3A5A40] to-[#2F4A33] rounded-3xl p-8 text-white shadow-lg mb-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl translate-x-1/3 -translate-y-1/2"></div>

          <div className="relative z-10 flex flex-col md:flex-row items-center gap-6">
            <div className="relative group">
              <div className="w-24 h-24 bg-[#E0E5D9] rounded-full flex items-center justify-center border-4 border-white/20 shadow-xl text-[#3A5A40]">
                <span className="font-serif text-3xl font-bold">
                  {profile.name ? profile.name.charAt(0).toUpperCase() : <Leaf />}
                </span>
              </div>
              <button className="absolute bottom-0 right-0 bg-white text-[#3A5A40] p-2 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity">
                <Camera className="w-4 h-4" />
              </button>
            </div>

            <div className="text-center md:text-left">
              <h2 className="text-2xl font-serif font-bold">{profile.name || "User"}</h2>
              <p className="text-emerald-100/80">{t('memberLabel')}</p>
            </div>
          </div>
        </div>

        {/* Details Form */}
        <div className="bg-white rounded-2xl shadow-sm border border-stone-100 overflow-hidden">
          <div className="p-6 border-b border-stone-100 flex items-center justify-between bg-stone-50/50">
            <h3 className="font-serif font-bold text-stone-800">{t('personalInfo')}</h3>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="text-sm font-medium text-[#3A5A40] hover:text-[#2F4A33] flex items-center gap-2"
            >
              {isEditing ? (
                <>{t('cancel')}</>
              ) : (
                <>
                  <Edit2 className="w-4 h-4" /> {t('editDetails')}
                </>
              )}
            </button>
          </div>

          <div className="p-6 md:p-8">
            {success && (
              <div className="mb-6 bg-emerald-50 text-emerald-700 p-3 rounded-xl text-sm border border-emerald-100 flex items-center gap-2">
                <Leaf className="w-4 h-4" /> {success}
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-6">
              {/* Name */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('fullName')}</label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all"
                  />
                </div>
              </div>

              {/* Email (Usually Read Only) */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                  <input
                    type="email"
                    disabled={true} // Usually email shouldn't be changed easily
                    value={profile.email}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-500 cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Phone Number */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('phone')}</label>
                <div className="relative">
                  <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                  <input
                    type="tel"
                    disabled={!isEditing}
                    value={profile.phone}
                    onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                    placeholder={isEditing ? t('phonePlaceholder') : t('phoneEmpty')}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all"
                  />
                </div>
              </div>

              {/* Age */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('age')}</label>
                <div className="relative">
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                  <input
                    type="number"
                    disabled={!isEditing}
                    value={profile.age || ""}
                    onChange={(e) => setProfile({ ...profile, age: parseInt(e.target.value) || 0 })}
                    placeholder={isEditing ? t('agePlaceholder') : t('ageEmpty')}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all"
                  />
                </div>
              </div>

              {/* Gender */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('gender')}</label>
                <div className="relative">
                  <Users className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                  <select
                    disabled={!isEditing}
                    value={profile.gender || ""}
                    onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all"
                  >
                    <option value="">{t('selectGender')}</option>
                    <option value="Male">{t('male')}</option>
                    <option value="Female">{t('female')}</option>
                    <option value="Other">{t('other')}</option>
                  </select>
                </div>
              </div>

              {/* Medical History */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('conditions')}</label>
                <div className="relative">
                  <Heart className="absolute left-4 top-3 w-5 h-5 text-stone-400" />
                  <textarea
                    disabled={!isEditing}
                    value={Array.isArray(profile.medical_history) ? profile.medical_history.join(", ") : profile.medical_history || ""}
                    onChange={(e) => setProfile({ ...profile, medical_history: e.target.value as any })}
                    placeholder={isEditing ? t('conditionsPlaceholder') : t('conditionsEmpty')}
                    rows={2}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all resize-none"
                  />
                </div>
              </div>

              {/* Medications */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('medications')}</label>
                <div className="relative">
                  <Pill className="absolute left-4 top-3 w-5 h-5 text-stone-400" />
                  <textarea
                    disabled={!isEditing}
                    value={Array.isArray(profile.medications) ? profile.medications.join(", ") : profile.medications || ""}
                    onChange={(e) => setProfile({ ...profile, medications: e.target.value as any })}
                    placeholder={isEditing ? t('medicationsPlaceholder') : t('medicationsEmpty')}
                    rows={2}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all resize-none"
                  />
                </div>
              </div>

              {/* Previous Conditions */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('prevConditions')}</label>
                <div className="relative">
                  <Heart className="absolute left-4 top-3 w-5 h-5 text-stone-400" />
                  <textarea
                    disabled={!isEditing}
                    value={Array.isArray(profile.previous_conditions) ? profile.previous_conditions.join(", ") : profile.previous_conditions || ""}
                    onChange={(e) => setProfile({ ...profile, previous_conditions: e.target.value as any })}
                    placeholder={isEditing ? t('prevConditionsPlaceholder') : t('prevConditionsEmpty')}
                    rows={2}
                    className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all resize-none"
                  />
                </div>
              </div>

              {/* Address */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-stone-500 uppercase tracking-wider">{t('address')}</label>
                <div className="space-y-3">
                  <div className="relative">
                    <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
                    <input
                      type="text"
                      disabled={!isEditing}
                      value={profile.address?.street || ""}
                      onChange={(e) => setProfile({ ...profile, address: { ...profile.address, street: e.target.value } })}
                      placeholder={isEditing ? t('streetPlaceholder') : t('streetEmpty')}
                      className="w-full pl-12 pr-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 disabled:pl-12 transition-all"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      disabled={!isEditing}
                      value={profile.address?.district || ""}
                      onChange={(e) => setProfile({ ...profile, address: { ...profile.address, district: e.target.value } })}
                      placeholder={isEditing ? t('districtPlaceholder') : t('districtEmpty')}
                      className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 transition-all"
                    />
                    <input
                      type="text"
                      disabled={!isEditing}
                      value={profile.address?.state || ""}
                      onChange={(e) => setProfile({ ...profile, address: { ...profile.address, state: e.target.value } })}
                      placeholder={isEditing ? t('statePlaceholder') : t('stateEmpty')}
                      className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 transition-all"
                    />
                  </div>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={profile.address?.pincode || ""}
                    onChange={(e) => setProfile({ ...profile, address: { ...profile.address, pincode: e.target.value } })}
                    placeholder={isEditing ? t('pincodePlaceholder') : t('pincodeEmpty')}
                    className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#3A5A40]/20 focus:border-[#3A5A40] disabled:bg-white disabled:border-transparent disabled:text-stone-600 transition-all"
                  />
                </div>
              </div>

              {isEditing && (
                <div className="pt-4 flex justify-end">
                  <button
                    type="submit"
                    disabled={saving}
                    className="bg-[#3A5A40] hover:bg-[#2F4A33] text-white px-6 py-3 rounded-xl font-bold shadow-lg shadow-[#3A5A40]/20 flex items-center gap-2 transition-all disabled:opacity-70"
                  >
                    {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                    {t('saveChanges')}
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}