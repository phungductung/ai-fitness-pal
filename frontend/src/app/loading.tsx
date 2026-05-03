"use client";

import React from 'react';

export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-background text-foreground">
      <div className="relative flex items-center justify-center">
        <div className="w-20 h-20 border-4 border-primary/20 rounded-full animate-pulse"></div>
        <div className="absolute w-20 h-20 border-t-4 border-primary rounded-full animate-spin"></div>
        <div className="absolute flex items-center justify-center">
          <svg className="w-10 h-10 text-primary animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m6.5 6.5 11 11"/><path d="m10 10 5.5 5.5"/><path d="m3 21 8-8"/><path d="m9 22 10-10"/><path d="m2 19 10-10"/><path d="m14 11 8 8"/><path d="m15 10 7-7"/><path d="m19 2 3 3"/>
          </svg>
        </div>
      </div>
      <div className="mt-8 text-center space-y-2">
        <h2 className="text-2xl font-bold gradient-text animate-pulse">AI Fitness Pal</h2>
        <p className="text-gray-400 animate-fade-in">Connecting to your fitness database...</p>
      </div>
    </div>
  );
}
