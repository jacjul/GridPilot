import { useState } from "react";

const EVForm = () => {
  const [kwh_EV, setKWHEV] = useState<number>(0);
  const [kwPeak, setKWPeak] = useState<number>(0);


  function handleSubmit(){
    if(kwh_EV ===0 || kwPeak===0){
        alert("kwh und kwPeak is nötig für Form submit")
        return;
    }

  }
  return (
    <div className="space-y-4 p-2">
      <div className="space-y-1">
        <label htmlFor="kwh_EV" className="block text-sm text-left font-medium text-slate-700">
          Battery Capacity
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            id="kwh_EV"
            type="number"
            value={kwh_EV}
            onChange={(e) => setKWHEV(Number(e.currentTarget.value))}
            min="0"
            step="0.5"
            placeholder="0.0"
          />
          <span className="text-sm text-slate-500">kWh</span>
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="kw_peak" className="block text-sm text-left font-medium text-slate-700">
          Max Charging Power
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            id="kw_peak"
            type="number"
            value={kwPeak}
            onChange={(e) => setKWPeak(Number(e.currentTarget.value))}
            min="0"
            step="0.5"
            placeholder="0.0"
          />
          <span className="text-sm text-slate-500">kW</span>
        </div>
      </div>
      <button className="border rounded-xl" onClick={()=>handleSubmit}>+ add EV</button>
    </div>
  );
};

export default EVForm;