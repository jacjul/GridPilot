import{useState} from "react"
import React from 'react'
import ConfigCard from "../components/ConfigCard"
import EVForm from "../components/EVForm"
import PVForm from "../components/PVForm"
import BESSForm from "../components/BESSForm"
import ElectricityForm from "../components/ElectricityForm"


//assets 
import {Car,SolarPanel,BatteryMedium,PlugZap} from "lucide-react"

const Stammdaten = () => {

    const [enabled,setEnabled] = useState({
        ev:false, pv:false, battery:false,electricity:false
    })

    const cards = [
  { key: "ev",icon:<Car className="h-5 w-5"/>,accent : "#e18617", title: "Electric Car", form: <EVForm /> },
  { key: "pv",icon:<SolarPanel className="h-5 w-5"/>,accent : "#dde720", title: "Photovoltaik", form: <PVForm /> },
  { key: "battery",icon:<BatteryMedium className="h-5 w-5"/>,accent : "#0fe625", title: "Battery", form: <BESSForm /> },
  { key: "electricity",icon:<PlugZap className="h-5 w-5"/>,accent : "#3b82f6", title: "Electricity", form: <ElectricityForm /> },
] as const;

    function handleToggle(key:keyof typeof enabled){
        setEnabled(prev=> ({...prev,
            [key]:!prev[key],}))
    }
    
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map(card =>
        <ConfigCard title={card.title} icon={card.icon} accent={card.accent} enabled={enabled[card.key]} onToggle={()=>handleToggle(card.key)}>
            <div className={enabled[card.key]? "":"pointer-events-none opacity-50"}>
                {card.form}
            </div>
            
        </ConfigCard>

        )}



    </div>
  )
}

export default Stammdaten