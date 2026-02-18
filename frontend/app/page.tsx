"use client";
import { useState } from 'react';
import FilterPanel from '@/components/FilterPanel';

// Type matching the Python backend response
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

export default function Home() {
  const [posts, setPosts] = useState<FlatDetails[]>([]);
  const [filteredPosts, setFilteredPosts] = useState<FlatDetails[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleScrape = async (url: string, filters: any) => {
    setLoading(true);
    setError('');

    // Clear previous results to avoid confusion
    setPosts([]);
    setFilteredPosts([]);

    try {
      const res = await fetch('http://localhost:8000/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_url: url,
          max_posts: 15, // Increase limit since we are filtering
          filters: filters
        }),
      });

      if (!res.ok) throw new Error('Scraping failed');

      const data = await res.json();
      setPosts(data.processed_posts);
      setFilteredPosts(data.processed_posts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (filters: any) => {
    if (!posts.length) return;

    const filtered = posts.filter(post => {
      // Rent Filter
      if (filters.minRent && post.rent && post.rent < filters.minRent) return false;
      if (filters.maxRent && post.rent && post.rent > filters.maxRent) return false;

      // Type Filter (Fuzzy match)
      if (filters.flatType && post.type) {
        if (!post.type.toLowerCase().includes(filters.flatType.toLowerCase())) return false;
      }

      // Gender Filter
      if (filters.gender && post.genderPreference) {
        // "Male" selected -> match "Male"
        // "Female" selected -> match "Female"
        if (post.genderPreference !== "Any" && post.genderPreference !== filters.gender) return false;
      }

      // Location Filter (Search in location or description)
      if (filters.location) {
        const search = filters.location.toLowerCase();
        const inLoc = post.location?.toLowerCase().includes(search);
        const inDesc = post.description?.toLowerCase().includes(search);
        if (!inLoc && !inDesc) return false;
      }

      return true;
    });
    setFilteredPosts(filtered);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans p-8">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">

        {/* Left Sidebar */}
        <div className="lg:col-span-1">
          <h1 className="text-2xl font-black mb-8 tracking-tight">
            Flat<span className="text-blue-600">Scraper</span>
          </h1>
          <FilterPanel
            loading={loading}
            onScrape={handleScrape}
            onFilterChange={handleFilterChange}
          />
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          <div className="mb-6 flex justify-between items-center">
            <h2 className="text-xl font-bold text-gray-800">Results</h2>
            <span className="text-sm text-gray-500 bg-white px-3 py-1 rounded-full shadow-sm">
              {filteredPosts.length} posts found
            </span>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 border border-red-100">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {loading ? (
              // Loading Skeleton
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
              filteredPosts.map((post, idx) => (
                <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 flex flex-col h-full">
                  <div className="flex justify-between items-start mb-4">
                    <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-lg text-xs font-bold uppercase">
                      {post.type || 'Unknown Type'}
                    </span>
                    <span className="text-lg font-bold text-gray-900">
                      {post.rent ? `₹${post.rent.toLocaleString()}` : 'Price on request'}
                    </span>
                  </div>

                  <p className="text-sm text-gray-600 mb-4 line-clamp-3 flex-grow">
                    {post.description || 'No description available'}
                  </p>

                  <div className="space-y-2 mt-auto pt-4 border-t border-gray-50 text-xs text-gray-500 font-medium">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                      <span className="truncate max-w-[150px]">{post.location || 'Unknown Location'}</span>
                    </div>

                    <div className="mt-2 flex gap-3 text-sm font-semibold">
                      {post.postUrl ? (
                        <a href={post.postUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 flex items-center gap-1 hover:underline">
                          Check Post
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                      ) : (
                        <span className="text-gray-400 cursor-not-allowed">Check Post</span>
                      )}

                      {/* See Description Modal Trigger or just expand? For now simple text */}
                      {/* <button className="text-gray-600 hover:text-gray-900">See description</button> */}
                    </div>

                    {post.contact && post.contact !== "Check Post" && (
                      <div className="flex items-center gap-2 text-green-600 mt-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>
                        {post.contact}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {filteredPosts.length === 0 && !loading && (
              <div className="col-span-full text-center py-20 text-gray-400">
                <p>No posts found. Try adjusting filters or scraping a group.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
