"use client";

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Admindashboard() {
  const router = useRouter();

  // Navigation handlers
  const handleCreateSubject = () => router.push('/sujets/nouveau');
  const handleStartNextPhase = () => router.push('/admin/phases/next');
  const handleStopSession = () => router.push('/admin/session/stop');

  return (
    <div className="bg-[#f8f9fc] w-full min-h-screen p-8 font-sans">
      {/* Top Banner */}
      <div className="flex justify-between items-center bg-green-50 border-l-4 border-green-500 p-3 rounded-r-lg mb-8 text-sm font-medium text-green-700">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
          Phase de rédaction
        </div>
        <div>18 jours restants</div>
        <div className="text-green-600/70">Clôture le 25 Juin 2024</div>
      </div>

      {/* Header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-[#0f2167]">Tableau de Bord</h1>
          <p className="text-gray-500 mt-1">Gestion académique de la session PFE 2024</p>
        </div>
        <button 
          onClick={handleCreateSubject}
          className="bg-[#0f2167] hover:bg-[#0a184a] transition-colors text-white px-5 py-2.5 rounded-lg font-bold flex items-center gap-2 text-sm"
        >
          <span>+</span> Nouveau Sujet
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        {/* Card 1: Users */}
        <Link href="/utilisateurs" className="bg-white p-5 rounded-xl shadow-sm border-b-4 border-blue-500 hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="flex justify-between items-start mb-2">
            <div className="bg-blue-50 p-2 rounded-lg text-blue-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
            </div>
            <span className="bg-green-100 text-green-600 text-xs font-bold px-2 py-1 rounded-full">+12%</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">1,248</p>
          <p className="text-xs text-gray-400 font-bold tracking-wider mt-1 uppercase">Utilisateurs</p>
        </Link>

        {/* Card 2: Teams */}
        <Link href="/equipes" className="bg-white p-5 rounded-xl shadow-sm border-b-4 border-yellow-400 hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="flex justify-between items-start mb-2">
            <div className="bg-yellow-50 p-2 rounded-lg text-yellow-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            </div>
            <span className="bg-gray-100 text-gray-600 text-[10px] font-bold px-2 py-1 rounded-full">Session Actuelle</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">312</p>
          <p className="text-xs text-gray-400 font-bold tracking-wider mt-1 uppercase">Équipes</p>
        </Link>

        {/* Card 3: Subjects */}
        <Link href="/sujets" className="bg-white p-5 rounded-xl shadow-sm border-b-4 border-purple-500 hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="flex justify-between items-start mb-2">
            <div className="bg-purple-50 p-2 rounded-lg text-purple-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            </div>
            <span className="bg-yellow-100 text-yellow-700 text-[10px] font-bold px-2 py-1 rounded-full">85% Validés</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">456</p>
          <p className="text-xs text-gray-400 font-bold tracking-wider mt-1 uppercase">Sujets</p>
        </Link>

        {/* Card 4: Oral Exams */}
        <Link href="/soutenances" className="bg-white p-5 rounded-xl shadow-sm border-b-4 border-teal-400 hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="flex justify-between items-start mb-2">
            <div className="bg-teal-50 p-2 rounded-lg text-teal-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 14l9-5-9-5-9 5 9 5z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"></path></svg>
            </div>
            <span className="bg-gray-100 text-gray-500 text-[10px] font-bold px-2 py-1 rounded-full">Prévues</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">128</p>
          <p className="text-xs text-gray-400 font-bold tracking-wider mt-1 uppercase">Soutenances</p>
        </Link>

        {/* Card 5: Pending Actions */}
        <Link href="/file-attente" className="bg-white p-5 rounded-xl shadow-sm border-b-4 border-red-500 hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="flex justify-between items-start mb-2">
            <div className="bg-red-50 p-2 rounded-lg text-red-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
            </div>
            <span className="bg-red-100 text-red-600 text-[10px] font-bold px-2 py-1 rounded-full">Urgent</span>
          </div>
          <p className="text-2xl font-bold text-red-500">24</p>
          <p className="text-[10px] text-gray-400 font-bold tracking-wider mt-1 uppercase leading-tight">Actions en<br/>Attente</p>
        </Link>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          {/* Phase Control */}
          <div className="bg-[#0f2167] text-white p-8 rounded-2xl shadow-md relative overflow-hidden">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-teal-400"></div>
              <p className="text-xs font-bold text-blue-200 tracking-wider">PHASE ACTUELLE</p>
            </div>
            <h2 className="text-3xl font-light mb-8">Choix des Sujets & Validation</h2>
            
            <div className="grid grid-cols-3 gap-4 mb-8">
              <div>
                <p className="text-xs text-blue-200 font-semibold mb-1">DÉBUT</p>
                <p className="text-lg font-bold">15 Mars 2024</p>
              </div>
              <div>
                <p className="text-xs text-blue-200 font-semibold mb-1">ÉCHÉANCE</p>
                <p className="text-lg font-bold">05 Avril 2024</p>
              </div>
              <div>
                <div className="flex justify-between items-end mb-1">
                  <p className="text-xs text-blue-200 font-semibold">PROGRESSION</p>
                  <p className="text-sm font-bold">65%</p>
                </div>
                <div className="w-full bg-[#1a3285] rounded-full h-1.5 mt-2">
                  <div className="bg-teal-400 h-1.5 rounded-full" style={{ width: '65%' }}></div>
                </div>
              </div>
            </div>
            
            <div className="flex gap-4">
              <button 
                onClick={handleStartNextPhase}
                className="bg-white text-[#0f2167] hover:bg-gray-100 transition-colors px-6 py-2.5 rounded-lg font-bold text-sm flex items-center gap-2"
              >
                Démarrer Phase Suivante
              </button>
              <button 
                onClick={handleStopSession}
                className="border border-blue-400/30 text-white hover:bg-blue-800/30 transition-colors px-6 py-2.5 rounded-lg font-bold text-sm"
              >
                Arrêter la session
              </button>
            </div>
          </div>

          {/* Activities List */}
          <div className="bg-white p-6 rounded-2xl shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-[#0f2167]">Activités Récentes</h3>
              <Link href="/activites" className="text-sm text-blue-600 hover:underline">Voir tout</Link>
            </div>
            
            <div className="relative pl-4 space-y-6">
              <div className="absolute left-[27px] top-4 bottom-4 w-px bg-gray-100"></div>
              {/* Simplified activity display - in a real app these would be mapped */}
              {[1, 2, 3].map((item) => (
                <div key={item} className="flex gap-4 relative z-10">
                  <div className="bg-blue-50 text-blue-600 p-2 rounded-full h-10 w-10 flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                  </div>
                  <div>
                    <p className="font-bold text-sm text-gray-800">Mise à jour #{item}</p>
                    <p className="text-sm text-gray-600">Action système effectuée avec succès.</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-[#0f2167]">File d'Attente</h3>
              <span className="bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">24 TOTAL</span>
            </div>

            <div className="space-y-3">
              {[
                { name: 'Réclamations', icon: 'red', count: 8, path: '/reclamations' },
                { name: 'Approvals', icon: 'blue', count: 12, path: '/validations' },
                { name: 'PVs', icon: 'green', count: 3, path: '/pvs' }
              ].map((task) => (
                <button 
                  key={task.name}
                  onClick={() => router.push(task.path)}
                  className="w-full flex items-center justify-between p-3 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <span className="font-bold text-sm text-gray-800">{task.name}</span>
                  <span className="text-gray-500 font-bold">{task.count} →</span>
                </button>
              ))}
            </div>

            <button 
              onClick={() => router.push('/admin/urgences')}
              className="w-full mt-4 text-center text-xs font-bold text-[#0f2167] uppercase tracking-wider py-2 hover:bg-gray-50 rounded-lg"
            >
              Traiter les dossiers urgents
            </button>
          </div>

          <div className="bg-gradient-to-br from-blue-100 to-blue-200 p-6 rounded-2xl shadow-sm relative overflow-hidden h-full flex flex-col justify-end">
            <div className="relative z-10 mt-12">
              <h3 className="text-[#0f2167] text-lg font-bold mb-2">Rapport de Performance</h3>
              <p className="text-sm text-blue-900/80 mb-4 leading-relaxed">Session 15% plus rapide.</p>
              <button 
                onClick={() => router.push('/rapports/performance')}
                className="bg-white text-[#0f2167] px-4 py-2 rounded-lg font-bold text-sm shadow-sm"
              >
                Consulter
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}