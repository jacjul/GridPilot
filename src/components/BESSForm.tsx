import { useState } from "react";

const BESSForm = () => {
  const [name, setName] = useState<string>("");
  const [kwh, setKwh] = useState<number>(13.5);
  const [kwPeakCharge, setKwPeakCharge] = useState<number>(5);
  const [kwPeakDischarge, setKwPeakDischarge] = useState<number>(5);

  return (
    <div className="space-y-4 p-2">
      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="bess_name">
          Name (optional)
        </label>
        <input
          id="bess_name"
          type="text"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
          placeholder="Home Battery"
        />
      </div>

      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="bess_kwh">
          Capacity
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            id="bess_kwh"
            type="number"
            value={kwh}
            onChange={(e) => setKwh(Number(e.currentTarget.value))}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            min="0"
            step="0.1"
            placeholder="13.5"
          />
          <span className="text-sm text-slate-500">kWh</span>
        </div>
      </div>

      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="bess_kw_charge">
          Max Charge Power
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            id="bess_kw_charge"
            type="number"
            value={kwPeakCharge}
            onChange={(e) => setKwPeakCharge(Number(e.currentTarget.value))}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            min="0"
            step="0.1"
            placeholder="5"
          />
          <span className="text-sm text-slate-500">kW</span>
        </div>
      </div>

      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="bess_kw_discharge">
          Max Discharge Power
        </label>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            id="bess_kw_discharge"
            type="number"
            value={kwPeakDischarge}
            onChange={(e) => setKwPeakDischarge(Number(e.currentTarget.value))}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
            min="0"
            step="0.1"
            placeholder="5"
          />
          <span className="text-sm text-slate-500">kW</span>
        </div>
      </div>
    </div>
  );
};

export default BESSForm;