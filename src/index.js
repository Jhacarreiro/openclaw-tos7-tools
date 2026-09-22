import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const configSchema=Type.Object({
  baseUrl:Type.String({description:"Base URL of the read-only TOS 7 bridge."}),
  tokenEnv:Type.Optional(Type.String({description:"Environment variable containing the bearer token."})),
  timeoutMs:Type.Optional(Type.Integer({minimum:1000,maximum:30000,default:8000}))
},{additionalProperties:false});

async function queryBridge(config,action,params){
  const token=config.tokenEnv?process.env[config.tokenEnv]:undefined;
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),config.timeoutMs??8000);
  try{
    const response=await fetch(`${config.baseUrl.replace(/\/+$/,"")}/v1/query`,{
      method:"POST",
      headers:{"content-type":"application/json",...(token?{authorization:`Bearer ${token}`}:{})},
      body:JSON.stringify({action,params}),
      signal:controller.signal
    });
    const body=await response.json().catch(()=>({error:"invalid_json_response"}));
    if(!response.ok)throw new Error(`tos7-tools bridge error ${response.status}: ${JSON.stringify(body)}`);
    return body;
  }finally{clearTimeout(timeout);}
}

const empty=Type.Object({},{additionalProperties:false});
export default defineToolPlugin({
  id:"tos7-tools",name:"TOS 7 Tools",
  description:"Read-only TerraMaster TOS 7 observability and inventory tools.",
  configSchema,
  tools:(tool)=>{
    const add=(name,description,action,parameters)=>tool({
      name,optional:true,description,parameters,
      execute:async(params,config)=>queryBridge(config,action,params)
    });
    return[
      add("tos_system","Read system information, CPU/RAM/load, uptime and temperatures.","system",empty),
      add("tos_power","Read fan, buzzer and UPS/NUT status.","power",empty),
      add("tos_storage","Read storage overview, disks, arrays or volumes.","storage",Type.Object({section:Type.Optional(Type.Union([Type.Literal("overview"),Type.Literal("disks"),Type.Literal("arrays"),Type.Literal("volumes")]))},{additionalProperties:false})),
      add("tos_network","Read network information and interface counters.","network",empty),
      add("tos_services","Read TOS services, file services, SSH state and failed units.","services",empty),
      add("tos_apps","Read TOS application inventory or one application status.","apps",Type.Object({name:Type.Optional(Type.String({maxLength:128}))},{additionalProperties:false})),
      add("tos_users","Read users, groups or online sessions.","users",Type.Object({section:Type.Optional(Type.Union([Type.Literal("users"),Type.Literal("groups"),Type.Literal("online")]))},{additionalProperties:false})),
      add("tos_shares","Read shared-folder inventory or one share.","shares",Type.Object({name:Type.Optional(Type.String({maxLength:128}))},{additionalProperties:false})),
      add("tos_security","Read firewall state/rules and optionally listening sockets.","security",Type.Object({includeListeners:Type.Optional(Type.Boolean())},{additionalProperties:false})),
      add("tos_logs","Read bounded TOS logs.","logs",Type.Object({category:Type.Optional(Type.String({maxLength:64})),level:Type.Optional(Type.String({maxLength:32})),limit:Type.Optional(Type.Integer({minimum:1,maximum:200}))},{additionalProperties:false})),
      add("tos_docker","Read Docker container state, health and restart metadata.","docker",Type.Object({name:Type.Optional(Type.String({maxLength:128}))},{additionalProperties:false})),
      add("tos_health_snapshot","Return an aggregated NAS health snapshot.","health_snapshot",empty)
    ];
  }
});
