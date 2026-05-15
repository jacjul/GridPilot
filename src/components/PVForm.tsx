import { useState } from "react";

const PVForm = () => {
    const [place, setPlace] = useState<string>("Dresden");
    const [declination, setDeclination] = useState<number>(20);
    const [azimuth, setAzimuth] = useState<number>(180);
    const [kwPeak, setKwPeak] = useState<number>(10);

  return (
        <div className="space-y-4 p-2">
            <div className="space-y-1">
                <label className="block text-sm text-left text-slate-700" htmlFor="pv_place">
                    Place
                </label>
                <div className="space-y-1">
                    <input
                        id="pv_place"
                        type="text"
                        value={place}
                        onChange={(e) => setPlace(e.currentTarget.value)}
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
                        placeholder="Dresden"
                    />
                    <p className="text-left text-xs text-slate-500">
                        Latitude and longitude will be resolved in the backend.
                    </p>
                </div>
            </div>

            <div className="space-y-1">
                <label className="block text-sm text-left text-slate-700" htmlFor="pv_declination">
                    Declination (Tilt)
                </label>
                <div className="grid grid-cols-[1fr_auto] items-center gap-2">
                    <input
                        id="pv_declination"
                        type="number"
                        value={declination}
                        onChange={(e) => setDeclination(Number(e.currentTarget.value))}
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
                        min="0"
                        max="90"
                        step="1"
                        placeholder="20"
                    />
                    <span className="text-sm text-slate-500">deg</span>
                </div>
            </div>

            <div className="space-y-1">
                <label className="block text-sm text-left text-slate-700" htmlFor="pv_azimuth">
                    Azimuth
                </label>
                <div className="grid grid-cols-[1fr_auto] items-center gap-2">
                    <input
                        id="pv_azimuth"
                        type="number"
                        value={azimuth}
                        onChange={(e) => setAzimuth(Number(e.currentTarget.value))}
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
                        min="0"
                        max="360"
                        step="1"
                        placeholder="180"
                    />
                    <span className="text-sm text-slate-500">deg</span>
                </div>
            </div>

            <div className="space-y-1">
                <label className="block text-sm text-left text-slate-700" htmlFor="pv_kw_peak">
                    Peak Power
                </label>
                <div className="grid grid-cols-[1fr_auto] items-center gap-2">
                    <input
                        id="pv_kw_peak"
                        type="number"
                        value={kwPeak}
                        onChange={(e) => setKwPeak(Number(e.currentTarget.value))}
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
                        min="0"
                        step="0.1"
                        placeholder="10"
                    />
                    <span className="text-sm text-slate-500">kWp</span>
        </div>
            </div>
    </div>
    );
};

export default PVForm;