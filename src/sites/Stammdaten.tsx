import EVForm from "../components/EVForm.tsx"
import PVForm from "../components/PVForm.tsx"
import PVManageForm from "../components/PVManageForm.tsx"
import BESSForm from "../components/BESSForm.tsx"
import ElectricityForm from "../components/ElectricityForm.tsx"
import ElectricityManageForm from "../components/ElectricityManageForm.tsx"
import BESSManageForm from "../components/BESSManageForm.tsx"
import EVOperationsForm from "../components/EVOperationsForm.tsx"


//assets 
import {Car,SolarPanel,BatteryMedium,PlugZap} from "lucide-react"

const Stammdaten = () => {
    const createCards = [
  { key: "ev",icon:<Car className="h-5 w-5"/>,accent : "#ea580c", title: "Create EV", form: <EVForm /> },
  { key: "pv",icon:<SolarPanel className="h-5 w-5"/>,accent : "#ca8a04", title: "Create PV", form: <PVForm /> },
  { key: "battery",icon:<BatteryMedium className="h-5 w-5"/>,accent : "#16a34a", title: "Create Battery", form: <BESSForm /> },
  { key: "electricity",icon:<PlugZap className="h-5 w-5"/>,accent : "#2563eb", title: "Create Tariff", form: <ElectricityForm /> },
] as const;

    const manageCards = [
      { key: "ev-ops", title: "EV Operations & Downtime", form: <EVOperationsForm /> },
      { key: "pv-manage", title: "PV Management", form: <PVManageForm /> },
      { key: "bess-manage", title: "Battery Management", form: <BESSManageForm /> },
      { key: "electricity-manage", title: "Electricity Tariff Management", form: <ElectricityManageForm /> },
    ] as const
    
  return (
    <section className="space-y-6 text-left">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-amber-50 via-white to-sky-50 p-4 shadow-sm">
        <h2 className="mb-1 text-xl font-semibold text-slate-900">Create Components</h2>
        <p className="mb-4 text-sm text-slate-600">Create EV, PV, battery, and electricity tariff entries here.</p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {createCards.map((card) => (
            <article key={card.key} className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
              <div className="mb-3 flex items-center gap-2">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full text-white" style={{ backgroundColor: card.accent }}>
                  {card.icon}
                </span>
                <p className="text-sm font-semibold text-slate-900">{card.title}</p>
              </div>
              {card.form}
            </article>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-indigo-50 p-4 shadow-sm">
        <h2 className="mb-1 text-xl font-semibold text-slate-900">Manage Components & Rules</h2>
        <p className="mb-4 text-sm text-slate-600">Select existing entries and run update or delete methods in separate management forms.</p>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {manageCards.map((card) => (
            <article key={card.key} className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
              <p className="mb-3 text-sm font-semibold text-slate-900">{card.title}</p>
              {card.form}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default Stammdaten