async function post(url,body={}) {
 const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const d=await r.json().catch(()=>({}));
 if(!r.ok) throw new Error(d.error||"Request failed");
 return d;
}
function openCreate(){document.getElementById("createOverlay")?.classList.add("open")}
function closeCreate(){document.getElementById("createOverlay")?.classList.remove("open")}
async function createList(){let n=document.getElementById("newListName").value.trim();if(!n)return;await post("/api/watchlist",{name:n});location.reload()}
async function renameList(id,name){let n=prompt("Rename your watchlist",name);if(n?.trim()){await post(`/api/watchlist/${id}/rename`,{name:n.trim()});location.reload()}}
async function deleteList(id){if(confirm("Delete this watchlist?")){await post(`/api/watchlist/${id}/delete`);location.reload()}}
async function addStock(id){let el=document.getElementById(`add-${id}`),s=el.value.trim().toUpperCase();if(!s)return;try{await post(`/api/watchlist/${id}/add`,{symbol:s});location.reload()}catch(e){alert(e.message)}}
async function markSeen(){try{await post("/api/mark-seen");location.reload()}catch(e){alert(e.message)}}
document.addEventListener("click",e=>{if(e.target.id==="createOverlay")closeCreate()});
if(window.POINTS){
 const ctx=document.getElementById("stockChart");
 if(ctx){
  new Chart(ctx,{type:"line",data:{datasets:[{data:window.POINTS,borderColor:"#ee72a6",backgroundColor:"rgba(238,114,166,.13)",fill:true,tension:.35,pointRadius:0,borderWidth:2}]},
  options:{responsive:true,maintainAspectRatio:false,parsing:false,interaction:{mode:"index",intersect:false},
  plugins:{legend:{display:false},tooltip:{displayColors:false,callbacks:{label:c=>"$"+Number(c.parsed.y).toLocaleString("en-US",{maximumFractionDigits:2})}}},
  scales:{x:{display:false},y:{grid:{color:"#eee7eb"},ticks:{color:"#8a7e93",callback:v=>"$"+Number(v).toLocaleString()}}}}});
 }
}
