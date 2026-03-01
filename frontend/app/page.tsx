"use client";
import { useState, useEffect, useRef } from 'react';
import FilterPanel from '@/components/FilterPanel';

interface FlatDetails {
  type?: string;
  rent?: number;
  location?: string;
  availableFrom?: string;
  description?: string;
  contact?: string;
  genderPreference?: string;
  postUrl?: string;
}

interface Tab {
  id: string;
  label: string;
  url: string;
  posts: FlatDetails[];
  filteredPosts: FlatDetails[];
  loading: boolean;
  error: string;
}



export default function Home() {
  const nextTabNum = useRef(2);

  const makeTab = (num: number): Tab => ({
    id: `tab-${Date.now()}-${num}`,
    label: `Session ${num}`,
    url: '', posts: [], filteredPosts: [], loading: false, error: ''
  });

  const [tabs, setTabs] = useState<Tab[]>([{
    id: 'tab-initial', label: 'Session 1', url: '', posts: [], filteredPosts: [], loading: false, error: ''
  }]);
  const [activeTabId, setActiveTabId] = useState('tab-initial');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [loginLoading, setLoginLoading] = useState(false);

  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0];

  const updateTab = (tabId: string, updates: Partial<Tab>) => {
    setTabs(prev => prev.map(t => t.id === tabId ? { ...t, ...updates } : t));
  };

  const checkAuthStatus = async () => {
    try {
      const res = await fetch('http://localhost:8000/auth/status');
      const data = await res.json();
      setIsLoggedIn(data.logged_in);
    } catch (e) {
      console.error("Auth status check failed", e);
    } finally {
      setAuthLoading(false);
    }
  };

  useEffect(() => { checkAuthStatus(); }, []);

  const handleScrape = async (url: string, filters: any) => {
    const tabId = activeTabId;
    // Extract a short label from the URL
    const groupName = url.replace(/.*groups\//, '').replace(/\/.*/, '').replace(/[?#].*/, '') || 'Group';
    updateTab(tabId, { loading: true, error: '', posts: [], filteredPosts: [], url, label: groupName });

    try {
      const res = await fetch('http://localhost:8000/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_url: url, max_posts: 15, filters }),
      });

      if (!res.ok) throw new Error('Scraping failed');
      const data = await res.json();

      if (data.processed_posts.length > 0 && data.processed_posts[0].error) {
        updateTab(tabId, { error: data.processed_posts[0].error, loading: false });
        setIsLoggedIn(false);
        return;
      }

      updateTab(tabId, { posts: data.processed_posts, filteredPosts: data.processed_posts, loading: false });
    } catch (err) {
      updateTab(tabId, { error: err instanceof Error ? err.message : 'Unknown error', loading: false });
    }
  };

  const handleLogin = async () => {
    setLoginLoading(true);
    try {
      await fetch('http://localhost:8000/auth/login', { method: 'POST' });
      await checkAuthStatus();
    } finally {
      setLoginLoading(false);
    }
  };

  const handleFilterChange = (filters: any) => {
    const tab = tabs.find(t => t.id === activeTabId);
    if (!tab || !tab.posts.length) return;
    const filtered = tab.posts.filter(post => {
      if (filters.minRent && post.rent && post.rent < filters.minRent) return false;
      if (filters.maxRent && post.rent && post.rent > filters.maxRent) return false;
      if (filters.flatType && post.type) {
        if (!post.type.toLowerCase().includes(filters.flatType.toLowerCase())) return false;
      }
      if (filters.gender && post.genderPreference) {
        if (post.genderPreference !== "Any" && post.genderPreference !== filters.gender) return false;
      }
      if (filters.location) {
        const search = filters.location.toLowerCase();
        const inLoc = post.location?.toLowerCase().includes(search);
        const inDesc = post.description?.toLowerCase().includes(search);
        if (!inLoc && !inDesc) return false;
      }
      return true;
    });
    updateTab(activeTabId, { filteredPosts: filtered });
  };

  const addTab = () => {
    const num = nextTabNum.current++;
    const newTab = makeTab(num);
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
  };

  const removeTab = (tabId: string) => {
    if (tabs.length <= 1) return; // Don't remove last tab
    const newTabs = tabs.filter(t => t.id !== tabId);
    setTabs(newTabs);
    if (activeTabId === tabId) {
      setActiveTabId(newTabs[newTabs.length - 1].id);
    }
  };

  // --- AUTH LOADING ---
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // --- LOGIN GATE ---
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
        <div className="max-w-md w-full bg-white p-10 rounded-3xl shadow-2xl border border-gray-100 text-center">
          <div className="w-20 h-20 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" /></svg>
          </div>
          <h1 className="text-3xl font-black mb-2 text-gray-900">RentLens</h1>
          <p className="text-gray-600 font-medium mb-8">Please log in to Facebook to start finding your next home.</p>

          <button
            onClick={handleLogin}
            disabled={loginLoading}
            className="w-full bg-[#1877F2] text-white py-4 rounded-2xl font-bold hover:bg-[#166fe5] transition-all active:scale-95 shadow-lg flex items-center justify-center gap-3 disabled:bg-gray-400"
          >
            {loginLoading ? (
              <>
                <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                Logging in... will return here automatically
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" /></svg>
                Continue with Facebook
              </>
            )}
          </button>
          <p className="text-xs text-gray-500 font-semibold mt-6">
            A secure browser window will open. After you log in, it will close automatically.
          </p>
        </div>
      </div>
    );
  }

  // --- MAIN APP ---
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans flex flex-col">
      {/* Tab Bar - Browser Style */}
      <div className="bg-white border-b border-gray-200 px-4 pt-3 flex items-end gap-0 overflow-x-auto">
        {tabs.map((tab, idx) => (
          <div
            key={tab.id}
            onClick={() => setActiveTabId(tab.id)}
            className={`group relative flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-sm font-medium cursor-pointer transition-all max-w-[220px] min-w-[120px] ${tab.id === activeTabId
              ? 'bg-gray-50 text-gray-900 border border-gray-200 border-b-gray-50 -mb-px z-10'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-150 border border-transparent hover:text-gray-700'
              }`}
          >
            {tab.loading && (
              <svg className="w-3.5 h-3.5 animate-spin text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            )}
            <span className="truncate">{tab.url ? tab.label : `Session ${idx + 1}`}</span>
            {tabs.length > 1 && (
              <button
                onClick={(e) => { e.stopPropagation(); removeTab(tab.id); }}
                className="ml-auto flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-gray-400 hover:bg-red-100 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
              >
                ×
              </button>
            )}
          </div>
        ))}
        {/* Add Tab Button */}
        <button
          onClick={addTab}
          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors mb-0.5 ml-1"
          title="New Session"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
        </button>

        {/* Spacer + Right Controls */}
        <div className="ml-auto flex items-center gap-3 pb-2">
          <div className="bg-green-50 px-3 py-1 rounded-lg border border-green-200 flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs font-bold text-green-700">Logged In</span>
          </div>
          <button
            onClick={async () => {
              await fetch('http://localhost:8000/auth/logout', { method: 'POST' });
              setIsLoggedIn(false);
            }}
            className="text-xs font-bold text-red-400 hover:text-red-600 transition-colors px-2 py-1 rounded-lg hover:bg-red-50"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Left Sidebar */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2 mb-6">
              <h1 className="text-2xl font-black tracking-tight">
                Rent<span className="text-blue-600">Lens</span>
              </h1>
            </div>
            <FilterPanel
              loading={activeTab.loading}
              onScrape={handleScrape}
              onFilterChange={handleFilterChange}
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="mb-6 flex justify-between items-center">
              <h2 className="text-xl font-bold text-gray-800">Listings</h2>
              <span className="text-sm text-gray-500 bg-white px-3 py-1 rounded-full shadow-sm border border-gray-100">
                {activeTab.filteredPosts.length} matches found
              </span>
            </div>

            {activeTab.error && (
              <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 border border-red-100 flex items-center gap-3">
                <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                <span className="text-sm font-medium">{activeTab.error}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {activeTab.loading ? (
                Array(4).fill(0).map((_, i) => (
                  <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-48 animate-pulse flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <div className="h-6 w-16 bg-gray-200 rounded"></div>
                        <div className="h-6 w-24 bg-gray-200 rounded"></div>
                      </div>
                      <div className="h-4 w-full bg-gray-200 rounded"></div>
                      <div className="h-4 w-2/3 bg-gray-200 rounded"></div>
                    </div>
                    <div className="pt-4 border-t border-gray-50 flex gap-2">
                      <div className="h-4 w-20 bg-gray-200 rounded"></div>
                    </div>
                  </div>
                ))
              ) : (
                activeTab.filteredPosts.map((post, idx) => (
                  <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 flex flex-col h-full group">
                    <div className="flex justify-between items-start mb-4">
                      <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-tight">
                        {post.type || 'Listing'}
                      </span>
                      <span className={`text-lg font-bold ${post.rent ? 'text-blue-600' : 'text-gray-400 text-sm'}`}>
                        {post.rent ? `₹${post.rent.toLocaleString()}/mo` : 'Price N/A'}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600 mb-4 line-clamp-3 flex-grow">
                      {post.description || 'No detailed description provided.'}
                    </p>

                    <div className="space-y-2 mt-auto pt-4 border-t border-gray-50 text-xs text-gray-400 font-medium">
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        <span className="truncate max-w-[150px]">{post.location || 'Not specified'}</span>
                      </div>

                      {post.genderPreference && post.genderPreference !== 'Any' && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                          <span>{post.genderPreference} preferred</span>
                        </div>
                      )}

                      <div className="mt-2 flex gap-4 text-sm font-bold">
                        {post.postUrl ? (
                          <a href={post.postUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 flex items-center gap-1.5 transition-colors">
                            View on Facebook
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                          </a>
                        ) : (
                          <span className="text-gray-300">Link Unavailable</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}

              {activeTab.filteredPosts.length === 0 && !activeTab.loading && (
                <div className="col-span-full py-32 flex flex-col items-center justify-center text-gray-400 bg-white/50 border border-dashed border-gray-200 rounded-3xl">
                  <svg className="w-12 h-12 mb-4 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                  <p className="font-medium">No listings yet.</p>
                  <p className="text-sm mt-1">Paste a Facebook Group URL and click Start Scrape.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
