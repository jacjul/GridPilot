import { useState } from "react";
import {postAPI, APIError} from "../fetchAPI"
import {useMutation} from "@tanstack/react-query"
type PVResponse= {
    message:string
    latitude:number
    longitude:number
}
type CreatePV={
    place:string
    declination:number
    azimuth:number
    kw_peak:number
    einspeiseverguetung:number
}
const PVForm = () => {
    const [place, setPlace] = useState<string>("Dresden");
    const [declination, setDeclination] = useState<number>(20);
    const [azimuth, setAzimuth] = useState<number>(180);
    const [kwPeak, setKwPeak] = useState<number>(10);
    const [einspeiseverguetung, setEinspeiseverguetung] = useState<number>(0.08);
    const [resolvedCoordinates, setResolvedCoordinates] = useState<string>("");

    const {mutate,isPending,error} = useMutation<PVResponse,APIError,CreatePV>({
        mutationFn: async(payload)=>{
            return await postAPI<PVResponse>("/api/pv",payload,
                {token : localStorage.getItem("access_token")??"",
                    credentials: "include"
                })
            
            },
        onSuccess: async()=>{
            setDeclination(0)
            setAzimuth(0)
            setKwPeak(0)
            setResolvedCoordinates("")
        },
        onSettled: (data)=>{
            if (data?.latitude !== undefined && data?.longitude !== undefined){
                setResolvedCoordinates(`${data.latitude.toFixed(5)}, ${data.longitude.toFixed(5)}`)
            }
        }

    })

    function handleSubmit(e:React.FormEvent<HTMLFormElement>){
        e.preventDefault()

        if (kwPeak <= 0){
            alert("kw Peak have to be higher 0")
            return
        }
        mutate({
                "place": place,
                "declination":declination,
            "azimuth":azimuth,
            "kw_peak":kwPeak,
            "einspeiseverguetung":einspeiseverguetung
        })
    }
  return (
        <form className="space-y-4 p-2" onSubmit={handleSubmit}>
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
                <label className="block text-sm text-left text-slate-700" htmlFor="pv_einspeiseverguetung">
                    Feed-in Tariff
                </label>
                <div className="grid grid-cols-[1fr_auto] items-center gap-2">
                    <input
                        id="pv_einspeiseverguetung"
                        type="number"
                        value={einspeiseverguetung}
                        onChange={(e) => setEinspeiseverguetung(Number(e.currentTarget.value))}
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
                        min="0"
                        step="0.001"
                        placeholder="0.08"
                    />
                    <span className="text-sm text-slate-500">EUR/kWh</span>
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

            <button className="border rounded-xl px-3 py-1" type="submit" disabled={isPending}>
                {isPending ? "Saving..." : "+ add PV"}
            </button>

            {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
            {resolvedCoordinates ? (
                <p className="text-left text-xs text-emerald-700">Resolved coordinates: {resolvedCoordinates}</p>
            ) : null}
    </form>
    );
};

export default PVForm;