const postAPI = async (url:string, payload?:URLSearchParams)=>{
    const response = await fetch(url, {
        method:"POST",
        body: JSON.stringify(payload),
        headers:{
            "Content-Type": "application/json"
        }
    })
    if (!response.ok){
        throw new Error(`HTTP Error: ${response.status}`)
    }
    return response.json() 
}

const getAPI =async(url:string)=>{
    const response = await fetch(url, {
        method:"GET"
    })
}