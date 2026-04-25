"use client";

import Dashboard from '@/components/Dashboard';
import Chat from '@/components/Chat';

export default function Home() {
  return (
    <main className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar / Left Navigation (Optional, could add later) */}
      
      {/* Main Dashboard Area */}
      <div className="flex-1 overflow-y-auto border-r border-white/5">
        <Dashboard />
      </div>

      {/* Right Chat Area */}
      <div className="w-[400px] flex flex-col p-4 bg-[#0d0d0d]">
        <Chat />
      </div>
    </main>
  );
}
