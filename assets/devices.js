/* Общее состояние устройств, категорий, подписей и журнала изменений Щитка 86. */
(function(global){
"use strict";
var STORE_KEY="shchitok2.state.v1";
var UNCATEGORIZED="uncategorized";

function clone(v){return JSON.parse(JSON.stringify(v));}
function trim(v){return String(v===undefined||v===null?"":v).replace(/^\s+|\s+$/g,"");}
function uid(prefix){return prefix+"-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,9);}
function key(panel,breaker){return panel+":"+breaker;}
function empty(){return {schema:1,categories:[],devices:[],links:{},breakers:{left:{},right:{}},breakerTimes:{},localOps:[],applied:{},migratedLegacy:false};}

function create(seedTree,panels){
  var state;
  function persist(){try{localStorage.setItem(STORE_KEY,JSON.stringify(state));}catch(e){}}
  function category(id){for(var i=0;i<state.categories.length;i++)if(state.categories[i].id===id)return state.categories[i];return null;}
  function device(id){for(var i=0;i<state.devices.length;i++)if(state.devices[i].id===id)return state.devices[i];return null;}
  function normalCategory(id){return category(id)?id:UNCATEGORIZED;}
  function setBreakerRaw(panel,breaker,value,at){
    if(!state.breakers[panel])state.breakers[panel]={};
    var defs=panels[panel]&&panels[panel].defs?panels[panel].defs:[];
    if(value===(defs[breaker]||""))delete state.breakers[panel][breaker];else state.breakers[panel][breaker]=value;
    state.breakerTimes[key(panel,breaker)]=at;
  }
  function descendants(id){
    var ids={},changed=true;ids[id]=true;
    while(changed){changed=false;for(var i=0;i<state.devices.length;i++){var d=state.devices[i];if(d.parentId&&ids[d.parentId]&&!ids[d.id]){ids[d.id]=true;changed=true;}}}
    return ids;
  }
  function mayWrite(entity,op,release){return !release||!entity||+(entity.updatedAt||0)<=+op.at;}

  function apply(op,release){
    var d=op.data||{},e,i,k,ids;
    if(op.type==="category_add"){
      e=d.category;if(!e||!e.id||category(e.id))return;
      state.categories.push(clone(e));
    }else if(op.type==="category_rename"){
      e=category(d.id);if(!e||e.id===UNCATEGORIZED||!mayWrite(e,op,release))return;
      e.name=trim(d.name)||e.name;e.updatedAt=op.at;
    }else if(op.type==="category_delete"){
      e=category(d.id);if(!e||e.id===UNCATEGORIZED||!mayWrite(e,op,release))return;
      for(i=0;i<state.devices.length;i++)if(state.devices[i].categoryId===d.id){state.devices[i].categoryId=UNCATEGORIZED;state.devices[i].updatedAt=op.at;}
      state.categories=state.categories.filter(function(c){return c.id!==d.id;});
    }else if(op.type==="device_add"){
      e=d.device;if(!e||!e.id||device(e.id))return;
      e=clone(e);e.categoryId=normalCategory(e.categoryId);e.parentId=e.parentId||null;state.devices.push(e);
      if(d.linkKey)state.links[d.linkKey]=e.id;
    }else if(op.type==="device_update"){
      e=device(d.id);if(!e||!mayWrite(e,op,release))return;
      if(d.name!==undefined)e.name=trim(d.name)||e.name;
      if(d.description!==undefined)e.description=trim(d.description);
      if(d.categoryId!==undefined){var nc=normalCategory(d.categoryId);if(nc!==e.categoryId)e.parentId=null;e.categoryId=nc;}
      e.updatedAt=op.at;
      if(d.breakerKey&&state.links[d.breakerKey]===e.id){
        var parts=d.breakerKey.split(":");setBreakerRaw(parts[0],+parts[1],e.name,op.at);
      }
    }else if(op.type==="device_delete"){
      e=device(d.id);if(!e||!mayWrite(e,op,release))return;
      ids=descendants(d.id);state.devices=state.devices.filter(function(x){return !ids[x.id];});
      for(k in state.links)if(ids[state.links[k]])delete state.links[k];
      var clears=d.clearBreakers||[];
      for(i=0;i<clears.length;i++){var c=clears[i];setBreakerRaw(c.panel,c.breaker,"",op.at);}
    }else if(op.type==="breaker_update"){
      k=key(d.panel,d.breaker);if(release&&+(state.breakerTimes[k]||0)>+op.at)return;
      setBreakerRaw(d.panel,d.breaker,trim(d.value),op.at);
    }
  }
  function commit(type,data){
    var op={id:uid("op"),at:Date.now(),type:type,data:data||{}};
    apply(op,false);state.localOps.push(op);state.applied[op.id]=true;persist();return op;
  }
  function seed(){
    state=empty();
    state.categories.push({id:UNCATEGORIZED,name:"Без категории",system:true,updatedAt:0});
    function walk(nodes,categoryId,parentId,path){
      for(var i=0;i<nodes.length;i++){
        var n=nodes[i],id="dev-base-"+path+i;
        state.devices.push({id:id,categoryId:categoryId,parentId:parentId,name:n.t,description:n.description||"",panel:n.p,breaker:n.i,warn:n.w?1:0,base:true,updatedAt:0});
        if(n.c&&n.c.length)walk(n.c,categoryId,id,path+i+"-");
      }
    }
    for(var i=0;i<seedTree.length;i++){
      var n=seedTree[i],id="cat-base-"+i;
      state.categories.push({id:id,name:n.t,description:"",panel:n.p,breaker:n.i,warn:n.w?1:0,base:true,updatedAt:0});
      if(n.c&&n.c.length)walk(n.c,id,null,i+"-");
    }
  }
  function load(){
    try{
      var saved=JSON.parse(localStorage.getItem(STORE_KEY)||"null");
      if(saved&&saved.schema===1&&saved.categories instanceof Array&&saved.devices instanceof Array){state=saved;return;}
    }catch(e){}
    seed();persist();
  }
  function migrateLegacy(){
    if(state.migratedLegacy)return;
    state.migratedLegacy=true;
    Object.keys(panels).forEach(function(panel){
      var edits={};try{edits=JSON.parse(localStorage.getItem(panels[panel].key)||"{}")||{};}catch(e){}
      Object.keys(edits).forEach(function(index){
        var value=trim(edits[index]);if(!value)return;
        var breaker=+index,cat=category(UNCATEGORIZED);
        var dev={id:uid("dev"),categoryId:cat.id,parentId:null,name:value,description:"",panel:panel,breaker:breaker,createdAt:Date.now(),updatedAt:Date.now()};
        commit("device_add",{device:dev,linkKey:key(panel,breaker)});
        commit("breaker_update",{panel:panel,breaker:breaker,value:value});
      });
    });
    persist();
  }
  function applyRelease(){
    var ops=global.SHCHITOK2_RELEASE_OPS instanceof Array?global.SHCHITOK2_RELEASE_OPS:[];
    for(var i=0;i<ops.length;i++){
      var op=ops[i];if(!op||!op.id||state.applied[op.id])continue;
      apply(clone(op),true);state.applied[op.id]=true;
    }
    persist();
  }

  load();migrateLegacy();applyRelease();

  return {
    state:state,persist:persist,category:category,device:device,key:key,
    labels:function(panel){if(!state.breakers[panel])state.breakers[panel]={};return state.breakers[panel];},
    linkedDevice:function(panel,breaker){return device(state.links[key(panel,breaker)]);},
    linkFor:function(d){
      var guard=0;
      while(d&&guard++<100){
        if(d.panel!==undefined&&d.panel!==null&&d.panel!==""&&d.breaker!==undefined&&d.breaker!==null)return {p:d.panel,i:+d.breaker,w:d.warn||0};
        d=d.parentId?device(d.parentId):category(d.categoryId);
      }
      return null;
    },
    children:function(categoryId,parentId){return state.devices.filter(function(d){return d.categoryId===categoryId&&(d.parentId||null)===(parentId||null);});},
    subtreeCount:function(id){return Object.keys(descendants(id)).length-1;},
    addCategory:function(name){
      var c={id:uid("cat"),name:trim(name),description:"",createdAt:Date.now(),updatedAt:Date.now()};
      commit("category_add",{category:c});return category(c.id);
    },
    renameCategory:function(id,name){commit("category_rename",{id:id,name:trim(name)});},
    deleteCategory:function(id){commit("category_delete",{id:id});},
    addDevice:function(data,panel,breaker,withLink){
      var d={id:uid("dev"),categoryId:normalCategory(data.categoryId),parentId:data.parentId||null,name:trim(data.name),description:trim(data.description),panel:panel,breaker:breaker,createdAt:Date.now(),updatedAt:Date.now()};
      commit("device_add",{device:d,linkKey:withLink?key(panel,breaker):null});return device(d.id);
    },
    updateDevice:function(id,data){
      var linkKey=null;Object.keys(state.links).forEach(function(k){if(state.links[k]===id)linkKey=k;});
      commit("device_update",{id:id,name:trim(data.name),description:trim(data.description),categoryId:data.categoryId,breakerKey:linkKey});
    },
    deleteDevice:function(id){
      var ids=descendants(id),clears=[];
      Object.keys(state.links).forEach(function(k){if(ids[state.links[k]]){var parts=k.split(":");clears.push({panel:parts[0],breaker:+parts[1],deviceId:state.links[k]});}});
      commit("device_delete",{id:id,clearBreakers:clears});
    },
    setBreaker:function(panel,breaker,value){commit("breaker_update",{panel:panel,breaker:breaker,value:trim(value)});},
    exportData:function(appVersion){
      return {format:"shchitok2-changes",formatVersion:1,application:{id:"com.dd.shchitok2",name:"Щиток 86",version:appVersion||""},exportedAt:new Date().toISOString(),operations:clone(state.localOps),snapshot:clone({categories:state.categories,devices:state.devices,links:state.links,breakers:state.breakers,breakerTimes:state.breakerTimes})};
    }
  };
}
global.ShchitokStore={create:create};
})(window);
