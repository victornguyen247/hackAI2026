import React, { useState, useEffect } from 'react';
import Landing from './components/Landing';
import Onboarding from './components/Onboarding';
import MapCanvas from './components/MapCanvas';
import ChatAgent from './components/ChatAgent';
import axios from 'axios';
import { LogOut, LayoutGrid, Sparkles, ChevronLeft } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [currentRoute, setCurrentRoute] = useState(null);
  const [progress, setProgress] = useState({});
  const [view, setView] = useState('landing'); // 'landing', 'onboarding', 'map'

  useEffect(() => {
    if (user) {
      fetchProgress();
      fetchProfile();
    }
  }, [user]);

  const fetchProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/users/${user}`);
      setUserProfile(res.data);
    } catch (err) {
      console.error("Error fetching profile", err);
    }
  };

  const fetchProgress = async () => {
    try {
      const res = await axios.get(`${API_BASE}/users/${user}/progress`);
      setProgress(res.data);
    } catch (err) {
      console.error("Error fetching progress", err);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentRoute(null);
    localStorage.removeItem('username');
    setView('landing');
  };

  const handleBackToDashboard = () => {
    setCurrentRoute(null);
    setView('landing');
  };

  const handleStartNew = () => {
    setView('onboarding');
  };

  const handleOnboardingComplete = (username, route) => {
    setUser(username);
    localStorage.setItem('username', username);
    setCurrentRoute(route);
    setView('map');
    fetchProfile(); // Fetch full profile after creation
  };

  const handleLogin = (username, map = null) => {
    setUser(username);
    localStorage.setItem('username', username);
    fetchProfile(); // Fetch profile on login
    if (map) {
      setCurrentRoute(map);
      setView('map');
    } else {
      setView('landing');
    }
  };

  return (
    <div className="min-h-screen bg-[#fdfaf3] text-[#1a1a1a] font-sans overflow-hidden paper-texture">
      {view === 'landing' && (
        <Landing 
            onLogin={handleLogin}
            onStartNew={handleStartNew}
            onLogout={handleLogout}
            initialUser={user}
        />
      )}

      {view === 'onboarding' && (
        <div className="relative">
            <button 
                onClick={handleBackToDashboard}
                className="absolute top-8 left-8 p-3 bg-white/50 hover:bg-white border border-[#dee2e6] rounded-xl flex items-center gap-2 font-medium text-slate-500 hover:text-slate-900 transition-all z-20 shadow-sm"
            >
                <ChevronLeft className="w-5 h-5" />
                Back to Dashboard
            </button>
            <Onboarding onSuccess={handleOnboardingComplete} initialUsername={user} />
        </div>
      )}

      {view === 'map' && currentRoute && (
        <div className="h-screen w-full relative animate-in fade-in duration-1000">
          <header className="absolute top-0 left-0 right-0 z-10 p-5 flex justify-between items-center bg-white/80 backdrop-blur-xl border-b border-[#dee2e6] shadow-sm">
            <div className="flex items-center gap-8">
                <button 
                  onClick={handleBackToDashboard}
                  className="flex items-center gap-3 px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-xl transition-all shadow-md group"
                >
                  <LayoutGrid className="w-4 h-4 group-hover:scale-110 transition-transform" />
                  <span className="hidden sm:inline">My Journeys</span>
                </button>

                <div className="flex items-center gap-4 pl-8 border-l border-[#dee2e6]">
                    <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center font-bold text-white shadow-sm ring-4 ring-slate-50">
                        {(userProfile?.first_name?.[0] || user?.[0])?.toUpperCase()}
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-[0.15em] leading-none mb-1.5">Explorer</span>
                        <span className="text-sm font-medium text-slate-900 leading-tight">
                            {userProfile?.first_name || user}
                        </span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-3">
                <div className="px-4 py-2 bg-[#f8f9fa] rounded-full text-[10px] font-bold text-slate-400 uppercase tracking-widest border border-[#e9ecef]">
                   Level {currentRoute.level || 1} Journey
                </div>
            </div>
          </header>
          
          <div className="absolute top-24 left-5 z-20">
              <ChatAgent goalContext={currentRoute.goal} />
          </div>
          
          <MapCanvas 
            routeId={currentRoute.id} 
            username={user} 
            progress={progress} 
            onProgressUpdate={fetchProgress}
          />
        </div>
      )}
    </div>
  );
}

export default App;
