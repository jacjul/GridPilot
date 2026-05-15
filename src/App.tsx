import { useState, memo,useCallback} from 'react'
import {Routes, Route} from "react-router-dom"
import Home from "./sites/Home"
import Stammdaten from "./sites/Stammdaten"
import Header from "./components/Header"
import './App.css'


function App() {

  return (
    <>
    <Header />
      <Routes >
        <Route path="/home" element={<Home />} />
        <Route path="/stammdaten" element={<Stammdaten />} />
      </Routes>
    </>
  )
}

export default App
