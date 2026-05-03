"use client";

import React from 'react';

export default function LoadingSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <header className="flex justify-between items-center">
        <div className="space-y-2">
          <div className="h-9 w-48 skeleton"></div>
          <div className="h-4 w-64 skeleton"></div>
        </div>
        <div className="h-10 w-40 skeleton"></div>
      </header>

      {/* Quick Stats Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass p-6 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 skeleton rounded-full"></div>
              <div className="h-4 w-24 skeleton"></div>
            </div>
            <div className="flex items-baseline space-x-2">
              <div className="h-9 w-16 skeleton"></div>
              <div className="h-4 w-8 skeleton"></div>
            </div>
            <div className="h-4 w-32 skeleton"></div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Skeleton */}
        <div className="lg:col-span-2 glass p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="h-7 w-40 skeleton"></div>
            <div className="h-5 w-24 skeleton"></div>
          </div>
          <div className="h-[300px] w-full skeleton opacity-50"></div>
        </div>

        {/* PR History Skeleton */}
        <div className="glass p-6">
          <div className="h-7 w-32 skeleton mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex justify-between items-center p-3">
                <div className="space-y-2">
                  <div className="h-4 w-24 skeleton"></div>
                  <div className="h-3 w-16 skeleton"></div>
                </div>
                <div className="h-5 w-12 skeleton"></div>
              </div>
            ))}
          </div>
          <div className="h-10 w-full skeleton mt-6"></div>
        </div>
      </div>
    </div>
  );
}
