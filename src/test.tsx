import {useState,memo, useCallback} from "react"

const Child = memo(({ont})=>{
  console.log("Child")
  return
  <button onClick={()=>ont}></button>
})

function App (){
  const [counter,setCounter] = useState(0)

  const handleClick = useCallback(()=>{console.log("hand")}, [])

  return(
    <>
    <div> test</div>
    <button onClick={()=>setCounter(counter +1)}></button>
    <Child ont={handleClick} />
    </>
  )
}
