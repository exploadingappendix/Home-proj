"use client";
import React from 'react';

export default function Navbar() {
  return (
    <nav className="bg-gray-800 text-white p-4 min-w-screen">
      <div className="container mx-auto flex justify-between items-center">
        <a href="/" className="text-lg font-bold">Path</a>
        <div>
          <a href="/dashboard" className="mr-4 hover:underline">Dashboard</a>
          <a href="/new-job" className="hover:underline">New Job</a>
        </div>
      </div>
    </nav>
  );
}
