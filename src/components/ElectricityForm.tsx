import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query"
import { postAPI, APIError } from "../fetchAPI"

type PriceType = "fixed" | "dynamic_EPEX";

type ElectricityCreate = {
  price_typ: PriceType
  fixed_price?: number
  market_zone?: string
  name?: string
}

type ElectricityResponse = {
  message: string
  new_price_id: number
}

const marketZones = [
  "AT",
  "BE",
  "CH",
  "CZ",
  "DE-LU",
  "DK1",
  "DK2",
  "FR",
  "HU",
  "IT-North",
  "NL",
  "NO2",
  "PL",
  "SI",
] as const;

const ElectricityForm = () => {
  const [name, setName] = useState<string>("");
  const [priceType, setPriceType] = useState<PriceType>("fixed");
  const [fixedPrice, setFixedPrice] = useState<number>(28);
  const [marketZone, setMarketZone] = useState<string>("DE-LU");

  const { mutate, isPending, error } = useMutation<ElectricityResponse, APIError, ElectricityCreate>({
    mutationFn: async (payload) => {
      return postAPI<ElectricityResponse>("/api/electricity", payload, {
        token: localStorage.getItem("access_token") ?? "",
        credentials: "include"
      })
    },
    onSuccess: async () => {
      setName("")
      setPriceType("fixed")
      setFixedPrice(28)
      setMarketZone("DE-LU")
    }
  })

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()

    if (priceType === "fixed" && fixedPrice <= 0) {
      alert("Fixed price must be > 0")
      return
    }

    mutate({
      price_typ: priceType,
      fixed_price: priceType === "fixed" ? fixedPrice : undefined,
      market_zone: priceType === "dynamic_EPEX" ? marketZone : undefined,
      name: name.trim() || undefined,
    })
  }

  return (
    <form className="space-y-4 p-2" onSubmit={handleSubmit}>
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

      <button className="border rounded-xl px-3 py-1" type="submit" disabled={isPending}>
        {isPending ? "Saving..." : "+ add electricity"}
      </button>

      {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
    </form>
  );
};

export default ElectricityForm;