"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Activity, Dumbbell, Utensils, Zap, Calendar, TrendingUp, Loader2, Play, Square, Volume2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

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
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setIsMounted(true);
    const fetchDashboardData = async () => {
      try {
        const response = await fetch('http://localhost:8000/dashboard-data');
        const json = await response.json();
        setData(json);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboardData();

    const handleDataUpdate = () => {
      console.log("Data update detected, refreshing dashboard...");
      fetchDashboardData();
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

  return (
    <div className="p-6 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold gradient-text">AI Fitness Pal</h1>
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
        <StatCard 
          icon={<Activity className="text-green-500" />} 
          label="Recovery" 
          value={isLoading ? "..." : (data.today_stats.recovery ?? 88).toString()} 
          unit="%" 
          sub={data.today_stats.recovery > 70 ? "Ready to train" : "Take it easy"} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weight Progress Chart */}
        <div className="lg:col-span-2 glass p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold flex items-center gap-2">
              <TrendingUp className="text-primary" /> Weight Progress
            </h3>
            <select className="bg-transparent border-none text-sm text-gray-400 focus:ring-0">
              <option>Last 7 Days</option>
              <option>Last 30 Days</option>
            </select>
          </div>
          <div className="h-[300px] w-full min-h-[300px] relative">
            {isMounted && (
              <ResponsiveContainer width="99%" height={300}>
                <AreaChart data={data.weight_progress.length > 0 ? data.weight_progress : weightData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
          <div className="space-y-4">
            {isLoading ? (
              <div className="flex justify-center items-center h-40">
                <Loader2 className="animate-spin text-primary" />
              </div>
            ) : data.prs.length > 0 ? (
              [...data.prs].reverse().slice(0, 4).map((pr: any, index: number) => (
                <PRItem key={index} exercise={pr.Exercise} weight={`${pr.Weight}kg`} date={pr.Date} />
              ))
            ) : (
              <p className="text-gray-500 text-center py-10">No PRs found</p>
            )}
          </div>
          <button className="w-full mt-6 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition">
            View All History
          </button>
        </div>
      </div>
    </div>
  );
}

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

function PRItem({ exercise, weight, date }) {
  return (
    <div className="flex justify-between items-center p-3 hover:bg-white/5 rounded-lg transition border border-transparent hover:border-white/5">
      <div>
        <div className="font-medium">{exercise}</div>
        <div className="text-xs text-gray-500">{date}</div>
      </div>
      <div className="text-primary font-bold">{weight}</div>
    </div>
  );
}
