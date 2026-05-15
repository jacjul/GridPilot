import { useState } from "react";

type PriceType = "fixed" | "dynamic_EPEX";

const marketZones = [
  "AT",
  "BE",
  "CH",
  "CZ",
  "DE-LU",
  "DE-AT-LU",
  "DK1",
  "DK2",
  "FR",
  "HU",
  "IT-North",
  "NL",
  "NO2",
  "PL",
  "SE4",
  "SI",
] as const;

const ElectricityForm = () => {
  const [name, setName] = useState<string>("");
  const [priceType, setPriceType] = useState<PriceType>("fixed");
  const [fixedPrice, setFixedPrice] = useState<number>(28);
  const [marketZone, setMarketZone] = useState<string>("DE-LU");

  return (
    <div className="space-y-4 p-2">
      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="electricity_name">
          Tariff Name (optional)
        </label>
        <input
          id="electricity_name"
          type="text"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
          placeholder="My Tariff"
        />
      </div>

      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="price_type">
          Price Type
        </label>
        <select
          id="price_type"
          value={priceType}
          onChange={(e) => setPriceType(e.currentTarget.value as PriceType)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
        >
          <option value="fixed">Fixed</option>
          <option value="dynamic_EPEX">Dynamic (EPEX)</option>
        </select>
      </div>

      {priceType === "fixed" && (
        <div className="space-y-1">
          <label className="block text-sm text-left text-slate-700" htmlFor="fixed_price">
            Fixed Price
          </label>
          <div className="grid grid-cols-[1fr_auto] items-center gap-2">
            <input
              id="fixed_price"
              type="number"
              value={fixedPrice}
              onChange={(e) => setFixedPrice(Number(e.currentTarget.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 tabular-nums outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
              min="0"
              step="0.1"
              placeholder="28"
            />
            <span className="text-sm text-slate-500">ct/kWh</span>
          </div>
        </div>
      )}

      <div className="space-y-1">
        <label className="block text-sm text-left text-slate-700" htmlFor="market_zone">
          Market Zone
        </label>
        <select
          id="market_zone"
          value={marketZone}
          onChange={(e) => setMarketZone(e.currentTarget.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200"
        >
          {marketZones.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default ElectricityForm;