import { useState, type FormEvent } from "react";
import {useMutation} from "@tanstack/react-query"
import {postAPI,APIError} from "../fetchAPI"
import { getAccessToken } from "../authStore"
type BESSCreate = {
    name?: string
    kw_peak_charge:number
    kw_peak_discharge?:number
    kwh:number
}

type BESSResponse = {
  message:string
  bess_id:number
}
const BESSForm = () => {
  const [name, setName] = useState<string>("");
  const [kwh, setKwh] = useState<number>(13.5);
  const [kwPeakCharge, setKwPeakCharge] = useState<number>(5);
  const [kwPeakDischarge, setKwPeakDischarge] = useState<number>(5);


  const {mutate,isPending,error} = useMutation<BESSResponse,APIError,BESSCreate>({
    mutationFn: async(payload)=>{
      return postAPI<BESSResponse>("/api/bess", payload,{token:getAccessToken() ?? "",
        credentials: "include"
      })
    },
    onSuccess: async()=>{
      setKwh(0)
      setKwPeakCharge(0)
      setKwPeakDischarge(0)
    }
  })

  function handleSubmit(e:FormEvent<HTMLFormElement>){
    e.preventDefault()
    if (kwh <= 0 || kwPeakCharge <= 0 || kwPeakDischarge <= 0){
      alert("Values must be > 0")
      return
    }
    mutate({
    name: name ?? "",
    kw_peak_charge:kwPeakCharge,
    kw_peak_discharge:kwPeakDischarge ??kwPeakCharge,
    kwh:kwh
    })
  }
  return (
    <form className="space-y-4 p-2" onSubmit={handleSubmit}>
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
            <button className="border rounded-xl px-3 py-1" type="submit" disabled={isPending}>
                {isPending ? "Saving..." : "+ add BESS"}
            </button>

            {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
    </form>
  );
};

export default BESSForm;