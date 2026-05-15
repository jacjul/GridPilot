import {Link, Links} from "react-router-dom"
import Home from "../sites/Home"
import Stammdaten from "../sites/Stammdaten"
import React from 'react'

const Header = () => {
  return (
    <nav className="flex flex-row gap-2 justify-end">
        
        <Link className="text-blue-500 hover:text-blue-700" to="/stammdaten" >Stammdaten</Link>
        <Link className="text-blue-500 hover:text-blue-700" to="/home">Home</Link>
        
    </nav>
  )
}

export default Header