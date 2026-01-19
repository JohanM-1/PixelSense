import React, { useState } from 'react';
import { LayoutDashboard, Settings, Video, Moon, Sun, Menu, X, FileText, Target } from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '../context/ThemeContext';

export default function Layout({ children, activeTab, onTabChange }) {
  const { theme, toggleTheme } = useTheme();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="flex h-screen w-full bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-sans transition-colors duration-300 overflow-hidden">
      
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 z-50">
        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-blue-700">
          PixelSense
        </h1>
        <button onClick={toggleSidebar} className="p-2 text-gray-600 dark:text-gray-300">
          {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        "fixed md:relative z-50 w-64 h-full flex-shrink-0 border-r border-gray-200 dark:border-gray-800 glass flex flex-col justify-between transition-transform duration-300 transform bg-white dark:bg-gray-900",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        <div>
          <div className="p-6 hidden md:block">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-blue-700">
              PixelSense
            </h1>
          </div>
          
          <div className="p-6 md:hidden">
             <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Menu</h2>
          </div>
          
          <nav className="px-4 space-y-2">
            <NavItem 
              icon={<Video size={20} />} 
              label="Analysis" 
              active={activeTab === 'analysis'} 
              onClick={() => { onTabChange('analysis'); closeSidebar(); }} 
            />
            <NavItem 
              icon={<Target size={20} />} 
              label="Grounding Bench" 
              active={activeTab === 'grounding'} 
              onClick={() => { onTabChange('grounding'); closeSidebar(); }} 
            />
            <NavItem 
              icon={<Settings size={20} />} 
              label="Settings" 
              active={activeTab === 'settings'} 
              onClick={() => { onTabChange('settings'); closeSidebar(); }} 
            />
            <NavItem 
              icon={<FileText size={20} />} 
              label="System Logs" 
              active={activeTab === 'logs'} 
              onClick={() => { onTabChange('logs'); closeSidebar(); }} 
            />
          </nav>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <button
            onClick={toggleTheme}
            className="flex items-center space-x-3 w-full px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
          >
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            <span className="font-medium">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-4 md:p-8 pt-20 md:pt-8 w-full">
        <div className="max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex items-center space-x-3 w-full px-4 py-3 rounded-xl transition-all duration-200",
        active 
          ? "bg-blue-500 text-white shadow-lg shadow-blue-500/30" 
          : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
      )}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}
