const names=["kamado","probe_1","probe_2","probe_3","probe_4"];
const show=v=>v===null||v===undefined?"--":Number(v).toFixed(1);
async function refresh(){
  const connection=document.querySelector(".connection");
  try{
    const response=await fetch("/api/status",{cache:"no-store"});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    document.getElementById("connection").textContent=data.connected?"Verbonden":"Niet verbonden";
    connection.classList.toggle("online",data.connected);
    document.getElementById("battery").textContent=data.battery===null?"--":`${data.battery}%`;
    names.forEach(name=>document.getElementById(name).textContent=show(data.temperatures[name]));
    document.getElementById("updated").textContent=data.last_update?new Date(data.last_update).toLocaleTimeString("nl-NL"):"--";
  }catch(error){
    connection.classList.remove("online");
    document.getElementById("connection").textContent="Webserverfout";
  }
}
refresh();setInterval(refresh,2000);
