"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Activity, Dumbbell, Utensils, Zap, Calendar, TrendingUp, Loader2, Play, Square, Volume2, Trash2, X } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import LoadingSkeleton from './LoadingSkeleton';

const weightData = [
  { date: 'Mon', weight: 85.5 },
  { date: 'Tue', weight: 85.2 },
  { date: 'Wed', weight: 84.9 },
  { date: 'Thu', weight: 85.1 },
  { date: 'Fri', weight: 84.7 },
  { date: 'Sat', weight: 84.5 },
  { date: 'Sun', weight: 84.3 },
];

export default function Dashboard() {
  const [isMounted, setIsMounted] = useState(false);
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [data, setData] = useState<any>({
    prs: [],
    weight_progress: [],
    today_stats: { calories: 0, protein: 0, weight: 0, recovery: 88 }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAllPRs, setShowAllPRs] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [selectedWorkoutDay, setSelectedWorkoutDay] = useState<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const filteredWeightData = data.weight_progress;

  const fetchDashboardData = async (background = false) => {
    if (background) setIsRefreshing(true);
    else setIsLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/dashboard-data');
      const json = await response.json();
      setData(json);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    setIsMounted(true);
    fetchDashboardData();

    const handleDataUpdate = () => {
      console.log("Data update detected, refreshing dashboard...");
      fetchDashboardData(true);
    };

    window.addEventListener('data-updated', handleDataUpdate);
    
    return () => {
      window.removeEventListener('data-updated', handleDataUpdate);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleMorningBriefing = async () => {
    if (isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    setIsBriefingLoading(true);
    try {
      const response = await fetch('http://localhost:8000/morning-briefing');
      const data = await response.json();
      
      if (data.status === 'success') {
        const audioUrl = `http://localhost:8000${data.audio_url}?t=${Date.now()}`;
        if (!audioRef.current) {
          audioRef.current = new Audio(audioUrl);
        } else {
          audioRef.current.src = audioUrl;
        }
        
        audioRef.current.onplay = () => setIsPlaying(true);
        audioRef.current.onended = () => setIsPlaying(false);
        audioRef.current.onerror = () => {
          setIsPlaying(false);
          console.error("Audio playback error");
        };
        
        await audioRef.current.play();
      }
    } catch (error) {
      console.error("Failed to fetch morning briefing:", error);
    } finally {
      setIsBriefingLoading(false);
    }
  };

  const handleDeletePR = async (id: string) => {
    setDeletingId(id);
    setConfirmId(null);
    try {
      const response = await fetch(`http://localhost:8000/personal-records/${id}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (result.status === 'success') {
        await fetchDashboardData(true);
      } else {
        alert("Error: " + result.message);
      }
    } catch (error) {
      console.error("Failed to delete PR:", error);
    } finally {
      setDeletingId(null);
    }
  };

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  return (
    <div className="p-6 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold gradient-text">AI Fitness Pal</h1>
            {isRefreshing && (
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-[10px] text-primary animate-pulse">
                <Loader2 size={10} className="animate-spin" />
                Updating...
              </div>
            )}
          </div>
          <p className="text-gray-400">Welcome back. Here is your current status.</p>
        </div>
        <div className="flex space-x-4">
          <button 
            onClick={handleMorningBriefing}
            disabled={isBriefingLoading}
            className={`px-4 py-2 rounded-lg border transition flex items-center gap-2 ${
              isPlaying 
                ? 'bg-primary text-black border-primary' 
                : 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/20'
            } ${isBriefingLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isBriefingLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : isPlaying ? (
              <Square size={18} fill="currentColor" />
            ) : (
              <Play size={18} fill="currentColor" />
            )}
            {isBriefingLoading ? 'Generating...' : isPlaying ? 'Stop Briefing' : 'Morning Briefing'}
            {isPlaying && <Volume2 size={18} className="animate-pulse" />}
          </button>
        </div>
      </header>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard 
          icon={<Utensils className="text-primary" />} 
          label="Daily Calories" 
          value={isLoading ? "..." : data.today_stats.calories.toLocaleString()} 
          unit="kcal" 
          sub={`${Math.max(0, 2800 - data.today_stats.calories)} left`} 
        />
        <StatCard 
          icon={<Zap className="text-secondary" />} 
          label="Protein" 
          value={isLoading ? "..." : data.today_stats.protein.toString()} 
          unit="g" 
          sub="Target: 200g" 
        />
        <StatCard 
          icon={<Dumbbell className="text-accent" />} 
          label="Current Weight" 
          value={isLoading ? "..." : (data.today_stats.weight || 84.3).toString()} 
          unit="kg" 
          sub="Latest entry" 
        />
        <WorkoutScheduleCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weight Progress Chart */}
        <div className="lg:col-span-2 glass p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold flex items-center gap-2">
              <TrendingUp className="text-primary" /> Weight Progress
            </h3>
            <div className="text-sm text-gray-400">Last 7 Days</div>
          </div>
          <div className="h-[300px] w-full min-h-[300px] relative">
            {isMounted && (
              <ResponsiveContainer width="99%" height={300}>
                <AreaChart data={filteredWeightData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorWeight" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                  <XAxis dataKey="date" stroke="#666" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#666" domain={['dataMin - 1', 'dataMax + 1']} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#141414', border: '1px solid #333', borderRadius: '8px' }}
                    itemStyle={{ color: '#00d4ff' }}
                  />
                  <Area type="monotone" dataKey="weight" stroke="#00d4ff" fillOpacity={1} fill="url(#colorWeight)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* PR History */}
        <div className="glass p-6">
          <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <Calendar className="text-secondary" /> Recent PRs
          </h3>
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {isLoading ? (
              <div className="flex justify-center items-center h-40">
                <Loader2 className="animate-spin text-primary" />
              </div>
            ) : data.prs.length > 0 ? (
              (showAllPRs ? data.prs : data.prs.slice(0, 4)).map((pr: any, index: number) => (
                <PRItem 
                  key={index} 
                  exercise={pr.Exercise} 
                  weight={`${pr.Weight}kg`} 
                  date={pr.Date} 
                  onDelete={() => setConfirmId(pr.Id)}
                  isDeleting={deletingId === pr.Id}
                />
              ))
            ) : (
              <p className="text-gray-500 text-center py-10">No PRs found</p>
            )}
          </div>
          {data.prs.length > 4 && (
            <button 
              onClick={() => setShowAllPRs(!showAllPRs)}
              className="w-full mt-6 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition text-sm font-medium"
            >
              {showAllPRs ? 'Show Less' : 'View All History'}
            </button>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="glass max-w-md w-full p-8 border-white/10 shadow-2xl animate-zoom-in">
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mb-2">
                <Trash2 size={32} />
              </div>
              <h3 className="text-2xl font-bold text-white">Delete Personal Record?</h3>
              <p className="text-gray-400">
                Are you sure you want to remove this record? This action cannot be undone.
              </p>
              <div className="flex gap-4 w-full pt-4">
                <button 
                  onClick={() => setConfirmId(null)}
                  className="flex-1 py-3 px-4 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => handleDeletePR(confirmId)}
                  className="flex-1 py-3 px-4 bg-red-500 text-white rounded-xl hover:bg-red-600 transition font-bold shadow-lg shadow-red-500/20"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Workout Exercises Modal */}
      {selectedWorkoutDay && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in" onClick={() => setSelectedWorkoutDay(null)}>
          <div className="glass max-w-md w-full p-8 border-white/10 shadow-2xl animate-zoom-in" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-2xl font-bold text-white">{selectedWorkoutDay.focus}</h3>
                <p className="text-primary font-medium">{selectedWorkoutDay.day}</p>
              </div>
              <button 
                onClick={() => setSelectedWorkoutDay(null)}
                className="p-2 hover:bg-white/5 rounded-full transition"
              >
                <X size={24} className="text-gray-400" /> 
              </button>
            </div>
            
            <div className="space-y-3">
              {selectedWorkoutDay.exercises.map((exercise: string, i: number) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/5 hover:border-primary/30 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-xs group-hover:bg-primary group-hover:text-black transition-colors">
                    {i + 1}
                  </div>
                  <span className="text-gray-200 font-medium">{exercise}</span>
                </div>
              ))}
            </div>

            <button 
              onClick={() => setSelectedWorkoutDay(null)}
              className="w-full mt-8 py-3 bg-primary text-black font-bold rounded-xl hover:bg-primary/90 transition shadow-lg shadow-primary/20"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );

  function WorkoutScheduleCard() {
    const [showFullSchedule, setShowFullSchedule] = useState(false);
    
    // Get current day (0=Sunday, 1=Monday, etc.)
    const todayIndex = new Date().getDay();
    // Map to our schedule index (Thứ 2 is index 0)
    const scheduleIndex = todayIndex === 0 ? 6 : todayIndex - 1;
    const todayWorkout = WORKOUT_SCHEDULE[scheduleIndex];
  
    return (
      <div className="glass p-6 relative overflow-hidden group">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Dumbbell className="text-green-500" />
            <span className="text-gray-400 font-medium">Daily Workout</span>
          </div>
          <div className="px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-[10px] text-green-500 font-bold uppercase tracking-wider">
            Live
          </div>
        </div>
        
        <div className="flex flex-col">
          <span className="text-2xl font-bold text-white mb-1">{todayWorkout.focus}</span>
          <div className="flex items-center gap-2">
            <span className="text-primary font-medium text-sm">{todayWorkout.day}</span>
            <span className="w-1 h-1 rounded-full bg-gray-600"></span>
            <span className="text-gray-500 text-xs uppercase tracking-tighter">Current Plan</span>
          </div>
        </div>
  
        <div className="mt-6 flex gap-2">
          <button 
            onClick={() => setSelectedWorkoutDay(todayWorkout)}
            className="flex-1 py-2.5 bg-primary/10 hover:bg-primary text-primary hover:text-black border border-primary/20 rounded-xl text-xs font-bold transition-all duration-300 flex items-center justify-center gap-2"
          >
            <Activity size={14} />
            Exercises
          </button>
          <button 
            onClick={() => setShowFullSchedule(true)}
            className="p-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors group/btn"
            title="Full Week Schedule"
          >
            <Calendar size={18} className="text-gray-400 group-hover/btn:text-white transition-colors" />
          </button>
        </div>
  
        {/* Full Week Schedule Modal */}
        {showFullSchedule && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fade-in" onClick={() => setShowFullSchedule(false)}>
            <div className="glass max-w-lg w-full p-8 border-white/10 shadow-2xl animate-zoom-in" onClick={e => e.stopPropagation()}>
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-3xl font-bold gradient-text">Weekly Schedule</h3>
                <button 
                  onClick={() => setShowFullSchedule(false)}
                  className="p-2 hover:bg-white/10 rounded-full transition-colors"
                >
                  <X size={24} className="text-gray-400" />
                </button>
              </div>
  
              <div className="grid gap-3">
                {WORKOUT_SCHEDULE.map((item, idx) => {
                  const isToday = idx === scheduleIndex;
                  return (
                    <div 
                      key={idx} 
                      className={`flex items-center justify-between p-4 rounded-2xl border transition-all duration-500 ${
                        isToday 
                          ? 'bg-primary/10 border-primary shadow-[0_0_20px_rgba(0,212,255,0.1)]' 
                          : 'bg-white/5 border-white/5 hover:border-white/10'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold ${
                          isToday ? 'bg-primary text-black' : 'bg-white/5 text-gray-400'
                        }`}>
                          {item.day.split(' ')[1] || 'CN'}
                        </div>
                        <div>
                          <div className={`font-bold ${isToday ? 'text-primary' : 'text-white'}`}>
                            {item.focus}
                          </div>
                          <div className="text-xs text-gray-500 font-medium uppercase tracking-widest">{item.day}</div>
                        </div>
                      </div>
                      <button 
                        onClick={() => setSelectedWorkoutDay(item)}
                        className={`p-2 rounded-lg transition-colors ${
                          isToday ? 'bg-primary/20 text-primary hover:bg-primary hover:text-black' : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-white'
                        }`}
                      >
                        <Activity size={18} />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
}

const WORKOUT_SCHEDULE = [
  { day: "Monday", focus: "Legs Focus", exercises: ["Squats", "Leg Press", "Lunges", "Leg Extensions", "Leg Curls", "Calf Raises"] },
  { day: "Tuesday", focus: "Chest Focus", exercises: ["Bench Press", "Incline Dumbbell Press", "Chest Flyes", "Pushups", "Dips"] },
  { day: "Wednesday", focus: "Back Focus", exercises: ["Pull-ups", "Lat Pulldowns", "Bent-over Rows", "Seated Cable Rows", "Deadlifts"] },
  { day: "Thursday", focus: "Legs Focus", exercises: ["Squats", "Leg Press", "Lunges", "Leg Extensions", "Leg Curls", "Calf Raises"] },
  { day: "Friday", focus: "Shoulders Focus", exercises: ["Overhead Press", "Lateral Raises", "Front Raises", "Reverse Flyes", "Shrugs"] },
  { day: "Saturday", focus: "Cardio", exercises: ["Running (30 mins)", "Cycling (20 mins)", "HIIT (15 mins)"] },
  { day: "Sunday", focus: "Activate Rest", exercises: ["Light Stretching", "Yoga", "Long Walk (45 mins)"] },
];

function StatCard({ icon, label, value, unit, sub }) {
  return (
    <div className="glass p-6">
      <div className="flex items-center space-x-3 mb-4">
        {icon}
        <span className="text-gray-400 font-medium">{label}</span>
      </div>
      <div className="flex items-baseline space-x-2">
        <span className="text-3xl font-bold">{value}</span>
        <span className="text-gray-500">{unit}</span>
      </div>
      <p className="text-sm text-gray-400 mt-2">{sub}</p>
    </div>
  );
}

function PRItem({ exercise, weight, date, onDelete, isDeleting }) {
  return (
    <div className="group flex justify-between items-center p-3 hover:bg-white/5 rounded-lg transition border border-transparent hover:border-white/5">
      <div className="flex-1">
        <div className="font-medium">{exercise}</div>
        <div className="text-xs text-gray-500">{date}</div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-primary font-bold">{weight}</div>
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          disabled={isDeleting}
          className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-all disabled:opacity-50"
          title="Remove PR"
        >
          {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
        </button>
      </div>
    </div>
  );
}
