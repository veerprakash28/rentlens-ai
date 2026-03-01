
import React from 'react';

interface FilterPanelProps {
    onScrape: (url: string, filters: any) => void;
    onFilterChange: (filters: any) => void;
    loading: boolean;
}

export default function FilterPanel({ onScrape, onFilterChange, loading }: FilterPanelProps) {
    const [url, setUrl] = React.useState('');
    const [minRent, setMinRent] = React.useState('');
    const [maxRent, setMaxRent] = React.useState('');
    const [flatType, setFlatType] = React.useState('');
    const [location, setLocation] = React.useState('');
    const [gender, setGender] = React.useState('');

    const getFilters = () => ({
        minRent: minRent ? Number(minRent) : undefined,
        maxRent: maxRent ? Number(maxRent) : undefined,
        flatType: flatType || undefined,
        location: location || undefined,
        gender: gender || undefined
    });

    const handleCancel = async () => {
        try {
            await fetch('http://localhost:8000/cancel', { method: 'POST' });
        } catch (e) {
            console.error("Cancel failed", e);
        }
    };

    const handleFilterUpdate = () => {
        onFilterChange({
            minRent: minRent ? Number(minRent) : null,
            maxRent: maxRent ? Number(maxRent) : null,
            flatType: flatType || null,
            location: location || null,
            gender: gender || null,
        });
    };

    React.useEffect(() => {
        handleFilterUpdate();
    }, [minRent, maxRent, flatType, location, gender]);

    return (
        <div className="bg-white/80 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-white/20 sticky top-4">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    Configuration
                </h2>
            </div>

            {/* Scraper Control */}
            <div className="mb-6 space-y-2">
                <label className="text-sm font-semibold text-gray-700">Facebook Group URL</label>
                <div className="flex flex-col gap-2">
                    <input
                        type="text"
                        placeholder="https://facebook.com/groups/..."
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                    />
                    <div className="flex gap-2">
                        <button
                            onClick={() => onScrape(url, getFilters())}
                            disabled={loading || !url}
                            className={`flex-1 px-6 py-3 rounded-xl font-medium whitespace-nowrap shadow-sm border border-transparent transition-all duration-300 ${loading
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200'
                                : 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg active:scale-95'
                                }`}
                        >
                            {loading ? 'Scraping...' : 'Start Scrape'}
                        </button>

                        {loading && (
                            <button
                                onClick={handleCancel}
                                className="px-6 py-3 rounded-xl font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-200 transition-all active:scale-95"
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
                <p className="text-xs text-gray-400">
                    The scraper will reuse your login session if available.
                </p>
            </div>

            <hr className="border-gray-100 my-6" />

            {/* Filters */}
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">Filters</h3>

            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 block">Flat Type</label>
                        <select
                            className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 bg-gray-50/50"
                            value={flatType}
                            onChange={(e) => setFlatType(e.target.value)}
                        >
                            <option value="">Any Type</option>
                            <option value="1BHK">1 BHK</option>
                            <option value="2BHK">2 BHK</option>
                            <option value="3BHK">3 BHK</option>
                            <option value="Single Room">Single Room</option>
                            <option value="Shared">Shared Room</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 block">Gender</label>
                        <select
                            className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 bg-gray-50/50"
                            value={gender}
                            onChange={(e) => setGender(e.target.value)}
                        >
                            <option value="">Any</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 block">Min Rent</label>
                        <input
                            type="number"
                            placeholder="5000"
                            className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 bg-gray-50/50"
                            value={minRent}
                            onChange={(e) => setMinRent(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 block">Max Rent</label>
                        <input
                            type="number"
                            placeholder="25000"
                            className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 bg-gray-50/50"
                            value={maxRent}
                            onChange={(e) => setMaxRent(e.target.value)}
                        />
                    </div>
                </div>

                <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Location</label>
                    <input
                        type="text"
                        placeholder="e.g. Koramangala, Indiranagar"
                        className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 bg-gray-50/50"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    />
                </div>
            </div>
        </div>

    );
}
