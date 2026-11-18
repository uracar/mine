var HP_MUL={ship:3.5,tank:1.25,plane:.5},HP_PER=1300;
// GLSL ES 3.00 shaders. Everything is written in linear HDR; the last pass does tone mapping.
const GLSL_HEAD='#version 300 es\nprecision highp float;\nprecision highp int;\nprecision highp sampler2D;\nprecision highp sampler2DShadow;\n';

// shared by every scene shader: atmosphere, noise, fog
const GLSL_COMMON=`
uniform vec3 uCam;            // camera position in world space
uniform vec3 uSunDir;         // direction TO the sun
uniform vec3 uSunCol;         // sunlight (HDR)
uniform vec3 uLightDir;       // the light that actually shines on the ground (sun by day, moon by night)
uniform vec3 uLightCol;
uniform vec3 uMoonDir;
uniform vec3 uSkyTop;
uniform vec3 uSkyHor;
uniform vec3 uAmbUp;
uniform vec3 uAmbDown;
uniform float uTime;
uniform float uNight;         // 0 day .. 1 night
uniform float uFcoef;         // logarithmic depth constant
uniform float uCloudH;
uniform float uCover;
uniform float uFogScale;
float hash12(vec2 p){vec3 p3=fract(vec3(p.xyx)*.1031);p3+=dot(p3,p3.yzx+33.33);return fract((p3.x+p3.y)*p3.z);}
float hash13(vec3 p3){p3=fract(p3*.1031);p3+=dot(p3,p3.zyx+31.32);return fract((p3.x+p3.y)*p3.z);}
// v5.0 value noise from a 256x256 lattice texture: one filtered fetch instead of four hashes (the smoothstep goes into the coordinate)
uniform sampler2D uNoiseTex;
float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return textureLod(uNoiseTex,(mod(i,256.)+f+.5)*(1./256.),0.).r;}
float fbm4(vec2 p){float s=0.,a=.5;for(int i=0;i<4;i++){s+=a*vnoise(p);p=p*2.03+vec2(11.7,5.3);a*=.5;}return s;}
float vnoise3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 vec2 rg=textureLod(uNoiseTex,(mod(i.xy+vec2(37.,17.)*i.z,256.)+f.xy+.5)*(1./256.),0.).rg;
 return mix(rg.x,rg.y,f.z);}
float fbm2(vec2 p){float s=0.,a=.5;for(int i=0;i<2;i++){s+=a*vnoise(p);p=p*2.03+vec2(11.7,5.3);a*=.5;}return s;}
vec3 lin(vec3 c){return pow(c,vec3(2.2));}
// sky colour without clouds: gradient, sun glow
vec3 skyBase(vec3 d){
 float h=clamp(d.y,0.,1.);
 vec3 c=mix(uSkyHor,uSkyTop,pow(h,.42));
 float s=max(dot(d,uSunDir),0.);
 c+=uSunCol*(pow(s,6.)*.012+pow(s,40.)*.05+pow(s,400.)*.5)*smoothstep(-.1,.05,uSunDir.y+.1);
 return c;
}
// distance haze: the colour comes from the sky in that direction so the haze glows towards the sun
vec3 fogColor(vec3 d){
 vec3 dd=normalize(vec3(d.x+1e-5,clamp(d.y,0.,.12),d.z));
 return skyBase(dd);
}
float fogAmount(float dist){float x=dist*uFogScale;return 1.-exp(-x*sqrt(x));}
// v5.0 sun shadows: one depth map from the sun around the player (ships, buildings, trees), four filtered taps
uniform sampler2DShadow uShadowMap;
uniform mat4 uShadowVP;       // camera-relative position -> the sun's clip space
uniform vec4 uShadowP;        // texel size (uv), normal offset (m), depth bias, on (0/1)
float sunShadow(vec3 rel,vec3 n){
 if(uShadowP.w<.5)return 1.;
 vec4 c=uShadowVP*vec4(rel+n*uShadowP.y,1.);
 float edge=max(abs(c.x),abs(c.y));if(edge>=1.||abs(c.z)>=1.)return 1.;
 vec3 s=c.xyz*.5+.5;s.z-=uShadowP.z;
 float t=uShadowP.x*.5;
 float v=(texture(uShadowMap,vec3(s.xy+vec2(-t,-t),s.z))+texture(uShadowMap,vec3(s.xy+vec2(t,-t),s.z))
        +texture(uShadowMap,vec3(s.xy+vec2(-t,t),s.z))+texture(uShadowMap,vec3(s.xy+vec2(t,t),s.z)))*.25;
 return mix(v,1.,smoothstep(.8,1.,edge));
}
vec4 logDepth(vec4 clip){clip.z=(log2(max(1e-6,1.+clip.w))*uFcoef-1.)*clip.w;return clip;}
`;

// ---------------- sky ----------------
const SKY_VS=GLSL_HEAD+`
uniform vec3 uRight; uniform vec3 uUp; uniform vec3 uFwd; uniform vec2 uTan;
out vec3 vDir;
void main(){
 vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2)*2.-1.;
 vDir=uFwd+uRight*p.x*uTan.x+uUp*p.y*uTan.y;
 gl_Position=vec4(p,1.,1.);
}`;
const SKY_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vDir; out vec4 oCol;
vec3 stars(vec3 d){
 vec3 p=d*260.;vec3 i=floor(p);vec3 f=fract(p)-.5;
 float h=hash13(i);float r=length(f);
 float s=step(.9965,h)*smoothstep(.3,.0,r);
 float tw=.7+.3*sin(uTime*(1.+h*3.)+h*40.);
 return vec3(.8,.85,1.)*s*tw*(.4+1.6*hash13(i+7.));
}
void main(){
 vec3 d=normalize(vDir);
 vec3 col=skyBase(d);
 // sun disc
 float sd=dot(d,uSunDir);
 col+=uSunCol*8.*smoothstep(.99965,.99985,sd)*step(0.,d.y+.02);
 // moon
 float md=dot(d,uMoonDir);
 float moon=smoothstep(.99975,.99985,md);
 vec2 mp=vec2(dot(d,normalize(cross(uMoonDir,vec3(0.,1.,0.)))),dot(d,normalize(cross(cross(uMoonDir,vec3(0.,1.,0.)),uMoonDir))))*60.;
 float crater=.75+.25*fbm2(mp*2.5);
 col+=vec3(.9,.95,1.)*moon*crater*1.5*uNight;
 col+=vec3(.5,.6,.9)*pow(max(md,0.),90.)*.05*uNight;
 // stars
 if(d.y>0.)col+=stars(d)*uNight*smoothstep(0.,.15,d.y)*1.5;
 // clouds: a thin layer and a thicker one, both lit by the sun
 if(d.y>.004){
  float t=(uCloudH-uCam.y)/d.y;
  if(t>0.){
   vec2 p=(uCam.xz+d.xz*t)*.00022+vec2(uTime*.0035,uTime*.0012);
   float n=fbm4(p)+.35*fbm4(p*3.1+4.7);
   float dens=smoothstep(uCover,uCover+.3,n);
   float fade=smoothstep(.004,.09,d.y);
   // look a little towards the sun to find how thick the cloud is on the way there
   vec2 sp=p+uSunDir.xz*.012/max(uSunDir.y,.15);
   float n2=fbm4(sp)+.35*fbm4(sp*3.1+4.7);
   float thick=clamp((n2-uCover)*2.4,0.,1.);
   vec3 lit=uLightCol*(1.15-.8*thick)*.55+uAmbUp*1.1;
   vec3 dark=uAmbUp*.75+uSkyHor*.25;
   vec3 cc=mix(lit,dark,smoothstep(.2,.9,dens*(1.-.3*n2)));
   cc+=uLightCol*pow(max(sd,0.),8.)*(1.-dens)*.35;           // silver lining
   cc=mix(cc,fogColor(d),smoothstep(.05,.0,d.y)*.7);
   col=mix(col,cc,clamp(dens*fade,0.,.96));
   // high wispy layer
   vec2 p2=(uCam.xz+d.xz*(t*2.4))*.00009+vec2(uTime*.006,0.);
   float w=smoothstep(.55,.9,fbm2(p2*vec2(1.,3.)+3.3));
   col=mix(col,mix(uSkyHor,vec3(1.),.7)*.5*(.4+uLightCol*.12),w*.18*fade);
  }
 }
 oCol=vec4(col,1.);
}`;

// ---------------- terrain ----------------
const TERRAIN_VS=GLSL_HEAD+GLSL_COMMON+`
in vec3 aGrid;                 // x,y = grid index, z = 1 for skirt vertices
uniform sampler2D uHT;         // r height, g normal.x, b normal.z, a moisture
uniform vec2 uOff;             // chunk origin relative to the camera (xz)
uniform float uSize;
uniform float uN;
uniform float uSkirt;
uniform mat4 uVP;
out vec3 vRel; out vec3 vN; out float vMoist; out float vLogW;
void main(){
 vec4 t=texelFetch(uHT,ivec2(aGrid.xy)+ivec2(1),0);
 float h=t.r-aGrid.z*uSkirt;
 vec2 xz=uOff+aGrid.xy*(uSize/uN);
 vRel=vec3(xz.x,h-uCam.y,xz.y);
 vN=vec3(t.g,sqrt(max(0.,1.-t.g*t.g-t.b*t.b)),t.b);
 vMoist=t.a;
 vec4 clip=uVP*vec4(vRel,1.);vLogW=1.+clip.w;gl_Position=clip;
}`;
const TERRAIN_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec3 vN; in float vMoist; in float vLogW;
uniform float uBias;
uniform float uDetail;
uniform vec4 uShade[24];       // canopy shadows: centre (xz, camera relative), radius, unused
uniform int uShadeN;
out vec4 oCol;
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 vec3 wp=vRel+uCam;
 vec3 N=normalize(vN);
 vec2 q=wp.xz;
 float h=wp.y;
 float near=1.-smoothstep(120.,1500.,dist);
 // fine surface detail from noise, only where it can be seen. Steep faces use 3D noise: a flat map seen from the side would smear.
 float steep=smoothstep(.1,.35,1.-N.y);
 if(dist<2600.&&uDetail>.5){
  float e=.35;
  float b1=vnoise(q*.9),b1x=vnoise((q+vec2(e,0.))*.9),b1z=vnoise((q+vec2(0.,e))*.9);
  float b2=vnoise(q*.11),b2x=vnoise((q+vec2(3.,0.))*.11),b2z=vnoise((q+vec2(0.,3.))*.11);
  vec2 g=vec2(b1x-b1,b1z-b1)/e*.2*near+vec2(b2x-b2,b2z-b2)/3.*.9*(1.-smoothstep(200.,1800.,dist));
  if(dist<60.){float b3=vnoise(q*4.),b3x=vnoise((q+vec2(.12,0.))*4.),b3z=vnoise((q+vec2(0.,.12))*4.);g+=vec2(b3x-b3,b3z-b3)/.12*.05*(1.-smoothstep(5.,60.,dist));}
  vec3 gw=vec3(g.x,0.,g.y);
  if(steep>.01){
   float c0=vnoise3(wp*.11),f2=1.-smoothstep(200.,1800.,dist);
   vec3 g3=vec3(vnoise3((wp+vec3(3.,0.,0.))*.11)-c0,vnoise3((wp+vec3(0.,3.,0.))*.11)-c0,vnoise3((wp+vec3(0.,0.,3.))*.11)-c0)/3.*.9*f2;
   if(dist<900.){float d0=vnoise3(wp*.9);g3+=vec3(vnoise3((wp+vec3(e,0.,0.))*.9)-d0,vnoise3((wp+vec3(0.,e,0.))*.9)-d0,vnoise3((wp+vec3(0.,0.,e))*.9)-d0)/e*.2*near;}
   g3-=N*dot(g3,N);
   gw=mix(gw,g3,steep);
  }
  N=normalize(N-gw);
 }
 float slope=1.-N.y;
 float nA=fbm4(q*.0045);               // large patches
 float nB=(dist<2400.&&uDetail>.5)?fbm4(q*.04+7.):.5;   // grass clumps
 float nC=vnoise(q*.5);                // fine grain
 float nD=vnoise(q*2.1+3.);
 // ---- materials ----
 vec3 sand=lin(vec3(.66,.58,.42)),wet=lin(vec3(.34,.29,.22));
 vec3 dry=lin(vec3(.20,.34,.24)),lush=lin(vec3(.05,.27,.22)),forest=lin(vec3(.02,.10,.09));   // v4.9 Pandora: blue-green ground
 vec3 rockA=lin(vec3(.44,.41,.38)),rockB=lin(vec3(.30,.26,.23)),dirt=lin(vec3(.36,.28,.18));
 vec3 snow=lin(vec3(.95,.97,1.));
 float scz=clamp(-vMoist,0.,1.);   // below zero the same channel carries scorching from explosions
 float mst=max(vMoist,0.);
 float pv=clamp((mst-1.)/2.,0.,1.);   // harbour pavement class rides in the moisture channel above 1
 float mo=mix(min(mst,1.),.5,clamp((mst-1.)*4.,0.,1.));
 float moist=clamp(mo+(nA-.5)*.5,0.,1.);
 vec3 grass=mix(dry,lush,smoothstep(.25,.7,moist));
 float far=smoothstep(150.,1800.,dist);
 float nE=vnoise(q*5.3+11.),nF=vnoise(q*17.+5.);
 float blade=mix(.75+.5*nE*(.6+.4*nF),1.,smoothstep(8.,70.,dist));
 grass*=blade*(.78+.44*nB)*(1.-.14*smoothstep(1200.,200.,dist)*(vnoise(q*.17+3.)-.5)*2.)*mix(.8+.4*nC*(.85+.3*nD),1.,far);
 // forest on gentle slopes up to the tree line
 float treeLine=700.+nA*260.;
 float forestW=smoothstep(.62,.78,mo+(nB-.5)*.04)*(1.-smoothstep(540.,700.,h))*(1.-smoothstep(.22,.42,slope));
 vec3 canopy=forest*(.55+.9*pow(nC*.6+nD*.4,1.4));
 vec3 land=mix(grass,mix(grass*.42,canopy,.7),forestW*.96);   // v4.8 a dark forest floor under the woods
 // alpine meadow darkening and bare earth patches
 land=mix(land,dirt*(.8+.4*nC),smoothstep(.55,.75,nA)*(1.-forestW)*.55);
 // v3.3 ground variety: field-sized patches of darker meadow, scrub and bare earth, worn tracks and scattered stones
 {
  float nm=vnoise(q*.016+21.)*.65+vnoise(q*.037-5.)*.35,nm2=(dist<3000.)?vnoise(q*.055+4.):.5;
  vec3 scrub=lin(vec3(.08,.20,.16))*(.75+.5*nC),heath=lin(vec3(.24,.19,.25)),meadow=mix(lush,dry,.5)*.92;
  float open=(1.-forestW)*(1.-pv);
  land=mix(land,meadow*(.85+.3*nB),smoothstep(.55,.7,nm)*.55*open);                               // greener fields
  land=mix(land,scrub,smoothstep(.6,.78,nm2+(nm-.5)*.6)*.3*open);   // v4.8 lighter scrub, so dark ground means forest                                // dark scrub and bushes
  land=mix(land,heath*(.8+.4*nD),smoothstep(.66,.8,1.-nm+(nC-.5)*.3)*.5*open);                    // dry heath, brownish
  {float fl=vnoise(q*.021+77.)*.6+vnoise(q*.09-13.)*.4;                                  // v4.9 drifts of purple, teal and magenta plants
   land=mix(land,lin(vec3(.30,.10,.34))*(.8+.4*nC),smoothstep(.66,.8,fl)*.55*open);
   land=mix(land,lin(vec3(.05,.30,.30))*(.8+.4*nD),smoothstep(.62,.78,1.-fl+(nB-.5)*.4)*.45*open);
   land=mix(land,lin(vec3(.20,.07,.18))*(.7+.6*nC),smoothstep(.8,.95,vnoise(q*.35+5.))*(1.-smoothstep(200.,1200.,dist))*.3*open);
   land=mix(land,lin(vec3(.05,.09,.06))*(.7+.6*nD),forestW*.5);}   // a dark mossy forest floor
  float tw=(1.-smoothstep(.004,.011,abs(vnoise(q*.0031+3.)-.5)))*(1.-smoothstep(1800.,4500.,dist));
  land=mix(land,dirt*(.7+.5*nC)*(1.-.25*smoothstep(.003,.0,abs(vnoise(q*.0031+3.)-.5)-.002)),tw*.85*open*(1.-smoothstep(.15,.35,slope)));   // dirt tracks across the country
 }
 land=mix(land,mix(lush*.8,dry,.5),smoothstep(treeLine-120.,treeLine+250.,h)*.6);
 // cliffs and rock with strata
 float sh=h+(nA-.5)*22.+nC*2.5+vnoise(q*.02)*12.;
 float sFade=1.-smoothstep(100.,1000.,dist);             // fine rock detail fades out so distant cliffs stay clean
 float strata=.5+.5*sin(sh*.11)*.6+.25*sin(sh*.31+1.7)*sFade;
 float crack=vnoise3(wp*vec3(.14,.3,.14));
 vec3 rock=mix(rockA,rockB,clamp(strata*(.2+.3*sFade)+mix(nC,vnoise3(wp*.5),steep)*.35+crack*.25*sFade,0.,1.));
 rock*=.88+.24*vnoise3(wp*.18);
 float rockW=smoothstep(.20,.40,slope+(nC-.5)*.12+smoothstep(900.,1500.,h)*.15);
 vec3 col=mix(land,rock,rockW);
 // snow
 float snowLine=1050.+(nA-.5)*250.;
 float snowW=smoothstep(snowLine,snowLine+160.,h+nC*30.)*(1.-smoothstep(.38,.6,slope));
 col=mix(col,snow,snowW);
 // beach and the wet band
 float beachW=1.-smoothstep(1.8,3.6,h+(nA-.5)*2.4+nC*.9+vnoise(q*.35)*.8);
 float rip=.5+.5*sin(dot(q,vec2(.93,.37))*1.6+vnoise(q*.12)*11.);
 float ripF=1.-smoothstep(30.,450.,dist);
 vec3 sandC=sand*(.80+.2*nC)*(1.-.22*rip*ripF)*(.9+.2*nD*(1.-smoothstep(10.,120.,dist)));
 sandC=mix(sandC,sandC*.8,smoothstep(.5,.8,vnoise(q*.045+9.))*.6);
 col=mix(col,sandC,beachW*(1.-snowW));
 col=mix(col,wet,(1.-smoothstep(.0,1.6,h+nC*.3))*beachW);
 // harbour ground: breakwater rock, asphalt, concrete
 if(pv>.03){
  float wr=smoothstep(.04,.12,pv)*(1.-smoothstep(.17,.21,pv));
  float wd=smoothstep(.2,.24,pv)*(1.-smoothstep(.29,.33,pv));   // v4.9 dirt road
  vec3 cdirt=lin(vec3(.33,.26,.17))*(.8+.35*nC);
  float wa=smoothstep(.3,.4,pv)*(1.-smoothstep(.55,.7,pv));
  float wc=smoothstep(.62,.8,pv);
  vec3 cr=lin(vec3(.36,.35,.33))*(.65+.7*nC);
  vec3 ca=lin(vec3(.16,.16,.17))*(.85+.3*nC);
  float seam=1.-.18*(1.-smoothstep(0.,.08,abs(fract(q.x/9.)-.5)*2.-.92))*(1.-smoothstep(60.,220.,dist))-.18*(1.-smoothstep(0.,.08,abs(fract(q.y/9.)-.5)*2.-.92))*(1.-smoothstep(60.,220.,dist));
  vec3 cc=lin(vec3(.38,.37,.36))*(.9+.14*vnoise(q*.35))*(.82+.3*vnoise(q*.045+4.))*(1.-.25*smoothstep(.62,.8,vnoise(q*.2+8.))*(1.-smoothstep(40.,260.,dist)))*seam;
  float pw=max(max(wr,wd),max(wa,wc));
  vec3 pc=(cr*wr+cdirt*wd+ca*wa+cc*wc)/max(wr+wd+wa+wc,1e-3);
  col=mix(col,pc,smoothstep(0.,.9,pw));
 }
 // scorched and churned ground from shells and bombs
 if(scz>.01){
  vec3 ash=mix(lin(vec3(.025,.02,.016)),lin(vec3(.17,.13,.10)),clamp(nC*.7+nD*.4-.15,0.,1.));
  col=mix(col,ash,clamp(scz*1.3,0.,.93)*(1.-pv));
 }
 // under water: sand to turquoise to deep blue; light patterns on the shallows
 float depth=-h;
 if(depth>0.){
  vec3 shallow=lin(vec3(.60,.88,.74)),lagoon=lin(vec3(.05,.66,.66)),mid=lin(vec3(.02,.40,.58)),deep=lin(vec3(.012,.13,.33)),abyss=lin(vec3(.004,.04,.15));
  vec3 sb=mix(sand*.9,shallow,smoothstep(0.,1.5,depth));
  sb=mix(sb,lagoon,smoothstep(.8,9.,depth));
  sb=mix(sb,mid,smoothstep(6.,32.,depth));
  sb=mix(sb,deep,smoothstep(24.,110.,depth));
  sb=mix(sb,abyss,smoothstep(90.,420.,depth));
 sb*=.85+.3*nC;
  col=sb;
  float c1=1.-abs(vnoise(q*.7+uTime*.35)*2.-1.),c2=1.-abs(vnoise(q*.7*1.4-uTime*.3+9.)*2.-1.);
  col*=1.+pow(c1*c2,3.)*2.2*smoothstep(25.,1.,depth);
 }
 // foam: a thin bright line where each wave washes up, and lace trailing behind it
 float shw=h-.14*sin(uTime*.8+wp.x*.021+wp.z*.016)-.05*sin(uTime*1.7+wp.x*.05-wp.z*.04);
 float wash=exp(-pow((shw+.02)/.14,2.));
 float lace=smoothstep(.40,.72,vnoise(q*1.1+vec2(uTime*.15,0.))*.55+vnoise(q*3.9+uTime*.1)*.45);
 float trail=.5+.5*sin(shw*22.-uTime*1.2+nC*4.);
 float trailW=smoothstep(-1.2,-.15,shw)*(1.-smoothstep(-.15,.0,shw));
 float foam=clamp(wash*(.5+.7*lace)+.4*trail*lace*trailW,0.,1.)*step(h,2.5);
 col=mix(col,lin(vec3(.80,.86,.90)),foam*.8);
 // ---- light ----
 float ndl=max(dot(N,uLightDir),0.);
 float sunUp=smoothstep(-.03,.08,uLightDir.y);
 float ao=.55+.45*N.y;
 ao*=.8+.2*smoothstep(0.,40.,h+30.)*1.;
 vec3 amb=mix(uAmbDown,uAmbUp,N.y*.5+.5)*ao;
 // shadows cast by the nearest giant crowns: stretched along the sun's direction when it is low
 float shade=1.,under=1.;
 if(uShadeN>0){
  vec2 L=normalize(uLightDir.xz+1e-4);vec2 Pp=vec2(-L.y,L.x);float el=clamp(1./max(uLightDir.y,.1),1.,3.5);
  for(int i=0;i<24;i++){
   if(i>=uShadeN)break;
   vec2 d=vRel.xz-uShade[i].xy;float r=uShade[i].z;
   float u=length(vec2(dot(d,L)/el,dot(d,Pp)))/r;
   shade*=1.-.72*(1.-smoothstep(.55,1.,u));
   under*=1.-.25*(1.-smoothstep(.0,.9,length(d)/r));
  }
 }
 float sunSh=sunShadow(vRel,normalize(vN));
 vec3 light=uLightCol*ndl*sunUp*shade*sunSh+amb*mix(1.,.8,1.-under)*mix(.8,1.,sunSh);
 // backlight through foliage and a little sheen on snow and wet sand
 light+=uLightCol*forestW*pow(max(dot(-V,uLightDir),0.),3.)*.12*sunUp;
 vec3 res=col*light;
 vec3 H=normalize(uLightDir+V);
 res+=uLightCol*pow(max(dot(N,H),0.),40.)*(snowW*.15+(1.-smoothstep(.0,.8,h))*.06*beachW)*sunUp;
 // ---- haze ----
 float fa=fogAmount(dist);
 res=mix(res,fogColor(-V),fa);
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5+uBias,0.,1.);
 oCol=vec4(res,1.);
}`;


// ---------------- giant trees and rocks (instanced) ----------------
// One mesh is shared by every tree; an instance carries position, height, crown width and trunk width.
const TREE_VS=GLSL_HEAD+GLSL_COMMON+`
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNrm;
layout(location=2) in vec2 aInfo;     // x: 0 trunk, 1 leaves or rock   y: height fraction
layout(location=3) in vec4 aInst;     // x, y, z (cell relative, world height), height
layout(location=4) in vec2 aInst2;    // rotation, tint
layout(location=5) in vec2 aInst3;    // crown width, trunk width
uniform mat4 uVP;
uniform vec2 uCellRel;
uniform float uWind;
uniform float uFadeR;                 // beyond this distance an instance has shrunk to nothing
uniform float uLod;                   // 0: draw the detailed mesh up close, 1: draw the cheap mesh far away
uniform float uLodR;
uniform float uType;                  // 1 tree, 2 rock
uniform float uTilt;                  // a damaged giant leans about its base by this angle, towards uTiltDir (xz)
uniform vec2 uTiltDir;
out vec3 vRel; out vec3 vN; out vec2 vInfo; out vec3 vP; out float vTint; out float vLogW;
void main(){
 vec3 base=vec3(uCellRel.x+aInst.x,aInst.y-uCam.y,uCellRel.y+aInst.z);
 float d=length(base);
 float f=1.-smoothstep(uFadeR*.72,uFadeR,d);
 float w=aInfo.x<.5?aInst3.y:aInst3.x;
 vec3 p=vec3(aPos.x*w,aPos.y*aInst.w,aPos.z*w)*f,n=normalize(aNrm/vec3(w,aInst.w,w));      // normals follow the stretched shape
 float cr=cos(aInst2.x),sr=sin(aInst2.x);
 p=vec3(cr*p.x+sr*p.z,p.y,-sr*p.x+cr*p.z);
 n=vec3(cr*n.x+sr*n.z,n.y,-sr*n.x+cr*n.z);
 if(uTilt!=0.){
  float ang=uTilt;vec3 o=p,c0=vec3(0.);
  if(aInfo.x>.5&&uType<1.5){                                       // the crown hangs from the trunk top and stays nearly flat as the trunk goes over
   ang=sign(uTilt)*min(abs(uTilt),.4);c0=vec3(0.,.78*aInst.w*f,0.);o=p-c0;
  }
  float ct=cos(ang),st=sin(ang),pa=dot(o.xz,uTiltDir),na=dot(n.xz,uTiltDir);
  float pa2=pa*ct+o.y*st,py=-pa*st+o.y*ct,na2=na*ct+n.y*st,ny=-na*st+n.y*ct;
  vec3 q=vec3(0.);q.xz=uTiltDir*pa2+(o.xz-uTiltDir*pa);q.y=py;
  vec3 cc=vec3(0.);                                                // where the pivot point of the crown has gone with the trunk
  if(aInfo.x>.5&&uType<1.5){float ctt=cos(uTilt),stt=sin(uTilt);cc.xz=uTiltDir*(c0.y*stt);cc.y=c0.y*ctt;}
  p=q+cc;n.xz=uTiltDir*na2+(n.xz-uTiltDir*na);n.y=ny;
 }
 float sway=aInfo.y*aInfo.y*aInst.w*f*(.003+.008*uWind)*step(uType,1.5);
 float ph=uTime*(.5+.4*uWind)+(uCam.x+base.x)*.002+(uCam.z+base.z)*.0017;
 p.x+=sin(ph)*sway;p.z+=cos(ph*.87)*sway*.7;
 vRel=base+p;vN=n;vInfo=aInfo;vP=aPos;vTint=aInst2.y;
 vec4 clip=uVP*vec4(vRel,1.);vLogW=1.+clip.w;gl_Position=clip;
 if(f<=0.||(uLod>.5)!=(d>=uLodR))gl_Position=vec4(0.,0.,-2.,1.);     // belongs to the other detail level
}`;
const TREE_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec3 vN; in vec2 vInfo; in vec3 vP; in float vTint; in float vLogW;
uniform float uType;                  // 0 conifer, 1 broadleaf, 2 rock
out vec4 oCol;
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 vec3 N=normalize(vN);if(dot(N,V)<0.)N=-N;                 // meshes are single-sided shells, so face the normal towards the viewer
 vec3 wp=vRel+uCam;
 float sunUp=smoothstep(-.03,.08,uLightDir.y);
 vec3 col;
 float occl=.5+.5*smoothstep(0.,.9,vInfo.y);
 float back=0.;
 vec3 emis=vec3(0.);
 float glowK=.06+uNight*1.6;                                  // v5.2 Pandora: the forest glows - faintly by day, brightly at night
 if(uType>1.5){                                                // rock
  float gr=vnoise(wp.xz*2.7+wp.y*3.1)*.5+vnoise(vec2(wp.x+wp.z,wp.y)*7.)*.5;
  vec3 r0=lin(vec3(.40,.38,.35)),r1=lin(vec3(.27,.25,.23)),r2=lin(vec3(.52,.45,.36));
  col=mix(mix(r0,r1,smoothstep(.2,.5,vTint)),r2,smoothstep(.6,.9,vTint))*(.65+.7*gr);
  col=mix(col,lin(vec3(.18,.26,.10)),smoothstep(.55,.9,N.y)*.45);   // moss on top faces
 }else if(vInfo.x<.5){                                         // trunk: long vertical bark furrows, whatever the size
  float ang=atan(vP.z,vP.x);
  float bark=vnoise(vec2(ang*6.,vP.y*2.5))*.6+vnoise(vec2(ang*19.,vP.y*9.))*.4;
  col=lin(vec3(.15,.11,.14))*(.45+.9*bark);
  N=normalize(N+vec3(cos(ang),0.,sin(ang))*(bark-.5)*.8);
  occl=.55+.45*smoothstep(0.,.35,vInfo.y);
  float lich=smoothstep(.8,.9,vnoise(vec2(ang*14.,vP.y*22.)))*(1.-smoothstep(.05,.45,vInfo.y));   // glowing lichen up the foot of the trunk
  emis+=lin(vec3(.25,.85,1.))*lich*glowK*.9;
 }else if(vInfo.x>1.5){                                        // hanging vines: thin dark strands with lighter tips
  float strand=vnoise(vec2(vP.x*vP.z*900.+vP.x*300.,vP.y*3.));
  col=mix(lin(vec3(.03,.13,.12)),lin(vec3(.16,.46,.40)),clamp(strand+(1.-vInfo.y)*.3,0.,1.));
  occl=.6;back=.5;
  emis+=mix(lin(vec3(.2,.9,1.)),lin(vec3(.85,.35,1.)),step(.6,vTint))*smoothstep(.55,.9,strand)*glowK*1.3;   // glowing strands
 }else{                                                        // leaves: three scales of colour variation
  vec3 la=lin(vec3(.035,.11,.07)),lb=lin(vec3(.11,.31,.17));   // natural greens with a Pandora teal cast   // v5.2 brighter, more saturated Pandora canopies
  float nd=1.-smoothstep(150.,900.,dist);
  float rn=vnoise3(wp*.06)*.5+vnoise3(wp*.2)*.3+vnoise3(wp*.65)*.2;               // v5.3 leaf masses at the scale of the tree
  {float edge=1.-abs(dot(N,V)),fk=1.-smoothstep(900.,1800.,dist);              // the outline of a crown breaks into sprays, with gaps through it
   if(rn<((edge-.3)*1.5+.06)*fk)discard;}
  occl*=.5+.5*smoothstep(.25,.7,rn);                                          // the gaps between leaf masses sit in shade
  float big=vnoise(wp.xz*.011+wp.y*.009),mid=vnoise(wp.xz*.06+wp.y*.07),fine=vnoise(wp.xz*.45+wp.y*.5);
  N=normalize(N+(vec3(vnoise(wp.xz*.05+wp.y*.07),vnoise(wp.zx*.06-wp.y*.05),vnoise(wp.yx*.05))-.5)*1.4*nd);
  vec3 leaf=mix(la,lb,clamp(vTint*.5+vInfo.y*.35+big*.45,0.,1.));
  if(vTint>.72)leaf=mix(leaf,lin(vec3(.46,.14,.50)),.8*(vTint-.72)*3.6);       // purple and magenta crowns
  if(vTint<.08)leaf=mix(leaf,lin(vec3(.06,.22,.30)),(.08-vTint)*8.);            // and a rare blue-teal one
  {float sp=smoothstep(.72,.9,vnoise3(wp*.45));                        // bioluminescent spots in the leaves
   emis+=mix(lin(vec3(.25,.95,.85)),lin(vec3(.95,.35,.9)),step(.55,vTint))*sp*glowK*.8*(1.-smoothstep(600.,2500.,dist));}
  float clump=smoothstep(.3,.7,vnoise(wp.xz*.085+wp.y*.12));           // leaf clusters
  col=leaf*(.5+.75*(clump*.4+mid*.35+fine*.25*nd));
  occl*=mix(.72,1.,smoothstep(-.8,.4,N.y));                       // the underside of a canopy sits in its own shade
  back=1.;
 }
 float diff=max(dot(N,uLightDir)*.85+.15,0.);                    // v5.3 harder light: the crown reads as masses in sun and shade
 vec3 amb=mix(uAmbDown,uAmbUp,N.y*.5+.5)*occl;
 float sunSh=sunShadow(vRel,N);
 vec3 light=uLightCol*diff*sunUp*mix(.55,1.,occl)*sunSh+amb*1.9+uLightCol*.06*sunUp;
 light+=uLightCol*back*pow(max(dot(-V,uLightDir),0.),3.)*.35*sunUp;
 light+=back*uLightCol*lin(vec3(.2,.6,.5))*max(-dot(N,uLightDir),0.)*.35*sunUp;   // light shining through thin leaves
 vec3 res=mix(col*light+emis,fogColor(-V),fogAmount(dist));
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);
 oCol=vec4(res,1.);
}`;

// ---------------- harbour structures (instanced shapes) ----------------
const BLD_VS=GLSL_HEAD+GLSL_COMMON+`
layout(location=0) in vec3 aPos;
layout(location=2) in vec4 aI0;   // x, y, z (relative to the port), yaw
layout(location=3) in vec3 aI1;   // size
layout(location=4) in vec4 aI2;   // colour, kind
uniform mat4 uVP;
uniform vec2 uOrigRel;
out vec3 vRel; out vec3 vLoc; out vec4 vCol; out vec3 vSz; out float vLogW; out float vYaw;
void main(){
 vec3 p=aPos*aI1;vLoc=p;vSz=aI1;
 float yaw=aI0.w;
 if(aI2.a>12.5&&aI2.a<13.5)yaw+=uTime*1.1;                 // radar bars turn
 if(aI2.a>11.5&&aI2.a<12.5&&aI1.y>1.&&aI1.z<.6)p.z+=sin(uTime*5.2+aPos.x*6.5+aI0.x*.07+aI0.z*.05)*aI1.x*.035*(.45+abs(aPos.x));   // flags ripple in the breeze (painted stripes are flat, so they stay put)
 float cr=cos(yaw),sr=sin(yaw);
 vec3 r=vec3(cr*p.x+sr*p.z,p.y,-sr*p.x+cr*p.z);
 vRel=vec3(uOrigRel.x+aI0.x,aI0.y-uCam.y,uOrigRel.y+aI0.z)+r;
 vCol=aI2;vYaw=yaw;
 vec4 clip=uVP*vec4(vRel,1.);vLogW=1.+clip.w;gl_Position=clip;
}`;
const BLD_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec3 vLoc; in vec4 vCol; in vec3 vSz; in float vLogW; in float vYaw;
uniform float uSmooth;            // 2 cylinder, 3 dome, 4 arch: curved faces get a smooth normal instead of the faceted one
out vec4 oCol;
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 vec3 N=normalize(cross(dFdx(vRel),dFdy(vRel)));if(dot(N,vRel)>0.)N=-N;
 vec3 nl=normalize(cross(dFdx(vLoc),dFdy(vLoc)));
 bool wall=abs(nl.y)<.15,top=abs(nl.y)>.9;
 if(uSmooth>1.5){
  vec3 a=vLoc/max(vSz,vec3(1e-3)),sz=max(vSz,vec3(1e-3));
  vec3 ln=vec3(0.);bool curved=false;
  if(uSmooth<2.5){curved=wall;ln=vec3(a.x/sz.x,0.,a.z/sz.z);}
  else if(uSmooth<3.5){curved=true;ln=vec3(4.*a.x/sz.x,a.y/sz.y,4.*a.z/sz.z);}
  else{curved=abs(nl.z)<.9;ln=vec3(4.*a.x/sz.x,a.y/sz.y,0.);}
  if(curved&&dot(ln,ln)>1e-8){float cy=cos(vYaw),sy=sin(vYaw);ln=normalize(ln);N=normalize(vec3(cy*ln.x+sy*ln.z,ln.y,-sy*ln.x+cy*ln.z));}
 }
 int kind=int(vCol.a+.5);
 vec3 base=lin(vCol.rgb);
 float c=abs(nl.x)>abs(nl.z)?vLoc.z:vLoc.x;
 float y=vLoc.y;
 vec3 wp=vRel+uCam;
 float seed=fract(vCol.r*57.3+vCol.g*31.7+vCol.b*13.1+vSz.x*.37);
 float fineK=1.-smoothstep(100.,420.,dist);
 vec3 emis=vec3(0.);
 float spec=0.,glass=0.;
 float grime=.86+.28*vnoise(wp.xz*.35+wp.y*.5);
 if(kind==9){                                                 // chain-link fence
  if(!top){
   vec2 g=vec2(c,y)*1.3;float wire=min(abs(fract(g.x+g.y)-.5),abs(fract(g.x-g.y)-.5));
   if(dist<130.){if(wire>.1&&y<vSz.y-.3&&y>.15)discard;}
   else if(hash12(floor(vec2(c,y)*2.6))<.55&&y>.2)discard;
  }
  base=lin(vec3(.52,.55,.55));
 }else if(kind==7){                                           // arched hangar: ribs, camouflage, big doors
  if(abs(nl.z)>.9){base=lin(vec3(.30,.33,.30))*(.8+.2*step(.5,fract(vLoc.x*.45)));}
  else{
   float rib=step(.9,fract(vLoc.z/7.));
   float cn=vnoise(wp.xz*.11+wp.y*.06)+.5*vnoise(wp.xz*.33);
   vec3 c1=base,c2=base*.45,c3=lin(vec3(.45,.40,.28));
   base=mix(mix(c1,c2,smoothstep(.55,.8,cn)),c3,smoothstep(.95,1.15,cn));
   base*=1.-.22*rib*fineK;spec=.08;
  }
 }else if(kind==16){                                         // town house: plastered walls with windows, roof in the territory's colour
  if(wall){
   float sd=fract(seed*13.7+vSz.x*.173+vSz.z*.091);
   vec3 pw=sd<.2?vec3(.82,.76,.62):sd<.4?vec3(.78,.60,.46):sd<.6?vec3(.86,.84,.80):sd<.8?vec3(.62,.70,.74):vec3(.72,.64,.52);
   vec2 cell=vec2(c/3.2,y/3.0);vec2 f=fract(cell);vec2 id=floor(cell);
   float win=step(.25,f.x)*step(f.x,.75)*step(.3,f.y)*step(f.y,.8)*step(1.4,y)*fineK;
   float lit=step(.5,hash12(id+vec2(seed*40.,seed*17.)))*uNight;
   vec3 gl=mix(lin(vec3(.09,.13,.18)),skyBase(reflect(-V,N))*.55,.45);
   base=mix(lin(pw)*grime*(.8+.2*smoothstep(0.,3.,y)),gl,win);glass=win;emis+=win*lit*lin(vec3(1.,.72,.38))*1.5;
  }else base*=(.72+.36*step(.5,fract(c*.8)))*(top?.9:1.);
 }else if(!wall&&!top&&kind==1){base=lin(vec3(.36,.2,.16))*(.8+.4*step(.5,fract(c*.9)));}   // pitched roofs: tile stripes
 else if(top){base*=.7+.3*vnoise(wp.xz*.8)*(kind==0||kind==1||kind==2?1.:0.);if(kind==1)base*=1.-.18*step(.85,fract(vLoc.x/5.))*fineK;}
 else if(kind==1){
  vec2 cell=vec2(c/3.6,y/3.3);vec2 f=fract(cell);vec2 id=floor(cell);
  float win=step(.22,f.x)*step(f.x,.78)*step(.3,f.y)*step(f.y,.8)*step(1.5,y)*fineK;
  float lit=step(.55,hash12(id+vec2(seed*40.,seed*17.)))*uNight;
  vec3 gl=mix(lin(vec3(.09,.13,.18)),skyBase(reflect(-V,N))*.55,.45);
  base=mix(base*grime,gl,win);glass=win;
  emis+=win*lit*lin(vec3(1.,.72,.38))*1.6;
  base*=.78+.22*smoothstep(0.,8.,y);
 }
 else if(kind==2){base*=(.88+.12*mix(.5,sin(c*8.),fineK))*grime*(.8+.2*smoothstep(0.,6.,y));}
 else if(kind==15){                                           // fuel tank: weld rings, catwalk line
  float ly=fract(y/2.5);base*=(.9+.1*mix(.5,sin(c*14.),fineK))*(1.-.3*smoothstep(.06,0.,min(ly,1.-ly))*fineK)*grime;
  base=mix(base,lin(vec3(.82,.1,.08)),step(vSz.y-2.2,y)*step(y,vSz.y-1.2)*.9);
 }
 else if(kind==5){float ly=fract(y/2.6);base*=(.88+.12*mix(.5,sin(c*13.),fineK))*(1.-.35*smoothstep(.05,0.,min(ly,1.-ly))*fineK);}
 else if(kind==4){base=mix(lin(vec3(.78,.1,.07)),lin(vec3(.93)),step(.5,fract(y/4.5)));}
 else if(kind==3){emis=base*(.5+6.*uNight);base*=.3;}
 else if(kind==14){float bl=pow(.5+.5*sin(uTime*2.4+wp.x*.01),6.);emis=lin(vec3(1.,.08,.04))*(.4+bl*(3.+uNight*14.));base=lin(vec3(.3,.04,.03));}
 else if(kind==6){vec2 hp=top?vLoc.xz/17.:vec2(0.);float rr=length(hp);base=lin(vec3(.22,.23,.23));base=mix(base,lin(vec3(.85,.75,.1)),(1.-smoothstep(0.,.05,abs(rr-.78)))*float(top));float hh=step(abs(hp.x),.3)*step(abs(hp.y),.07)+step(abs(hp.x),.07)*step(abs(hp.y),.3);base=mix(base,lin(vec3(.95)),hh*float(top)*step(rr,.7));}
 else if(kind==8){base*=grime;spec=.35;}
 else if(kind==11){                                           // earth-covered bunker
  float n1=vnoise(wp.xz*.7)*.6+vnoise(wp.xz*2.3)*.4;
  base=mix(lin(vec3(.12,.20,.07)),lin(vec3(.28,.30,.12)),n1);
  if(abs(nl.y)<.5&&wp.y<vLoc.y+500.)base=lin(vec3(.30,.30,.28))*grime;
 }
 else if(kind==12){base=lin(vCol.rgb);}
 else{base*=grime*(.82+.18*smoothstep(0.,4.,y));}
 float wyB=vRel.y+uCam.y;
 {float wetB=1.-smoothstep(.2,2.6,wyB);base=mix(base,base*lin(vec3(.42,.5,.4)),wetB*.85);              // piers and quay walls: wet, green at the waterline
  base*=1.-.18*smoothstep(.0,.7,vnoise(wp.xz*.5+wp.y*2.))*smoothstep(3.5,.5,y)*fineK;}                     // dirt and grime gathered at the foot of every wall
 float sunUp=smoothstep(-.03,.08,uLightDir.y);
 float diff=max(dot(N,uLightDir),0.);
 vec3 amb=mix(uAmbDown,uAmbUp,N.y*.5+.5)*(.55+.45*smoothstep(0.,6.,y+(top?6.:0.)));
 float sunSh=sunShadow(vRel,N);
 vec3 res=base*(uLightCol*diff*sunUp*sunSh+amb*1.5*mix(.8,1.,sunSh))+emis;
 vec3 H=normalize(uLightDir+V);
 res+=uLightCol*sunUp*sunSh*pow(max(dot(N,H),0.),glass>0.?60.:24.)*(glass*.9+spec);
 {float ndvB=max(dot(N,V),0.),frB=.04+.96*pow(1.-ndvB,5.);vec3 envB=skyBase(reflect(-V,N));
  res=mix(res,envB,clamp(glass*(.35+frB)+spec*(.3+frB)*.6+frB*.06,0.,.8)*(1.-smoothstep(300.,900.,dist)));}  // glass towers and tin roofs mirror the sky
 res=mix(res,fogColor(-V),fogAmount(dist));
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);
 oCol=vec4(res,1.);
}`;

// ---------------- roads: ribbons laid along each route ----------------
const ROAD_VS=GLSL_HEAD+GLSL_COMMON+`
layout(location=0) in vec3 aPos;      // x, z relative to the piece origin, y in the world
layout(location=1) in vec2 aUV;       // across (-1..1), along (metres)
uniform mat4 uVP;
uniform vec2 uOrigRel;
out vec3 vRel; out vec2 vUV; out float vLogW;
void main(){
 vec3 rel=vec3(uOrigRel.x+aPos.x,aPos.y-uCam.y,uOrigRel.y+aPos.z);
 rel.y+=.16+length(rel)*.0012;                              // sit just above the ground, more so far away where chunks are coarse
 vRel=rel;vUV=aUV;
 vec4 clip=uVP*vec4(rel,1.);vLogW=1.+clip.w;gl_Position=clip;
}`;
const ROAD_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec2 vUV; in float vLogW;
uniform float uFarR;
uniform float uMain;
uniform vec4 uHoles[24];
out vec4 oCol;
const float HALF=7.5;                                         // half width of the whole ribbon, metres
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 vec3 wp=vRel+uCam;
 float m=vUV.x*HALF,a=abs(m),s=vUV.y;
 float near=1.-smoothstep(120.,700.,dist);
 // v4.9 dirt roads: packed earth, two wheel ruts, puddles; grass between the ruts on the quiet tracks, churned mud on the main road
 bool mainR=uMain>.5;
 float wear=vnoise(wp.xz*.05)*.5+vnoise(wp.xz*.4)*.3*near+vnoise(wp.xz*2.3)*.2*near;
 vec3 earth=lin(vec3(.35,.28,.19))*(.72+.5*wear);
 vec3 mud=lin(vec3(.17,.13,.09))*(.8+.4*vnoise(wp.xz*1.7));
 vec3 grassC=lin(vec3(.2,.27,.11))*(.75+.45*vnoise(wp.xz*1.3));
 float rut=1.-smoothstep(mainR?.45:.3,mainR?1.1:.75,abs(a-1.7));
 vec3 col=mix(earth,mud,rut*(mainR?.85:.5));
 float crown=1.-smoothstep(.55,1.05,a);
 col=mix(col,mainR?mix(earth,mud,.4):grassC,crown*(mainR?.55:.8));
 float pud=smoothstep(.7,.76,vnoise(wp.xz*.06+4.))*rut;
 col=mix(col,lin(vec3(.07,.08,.09)),pud*.75*near);
 float verge=smoothstep((mainR?4.4:3.)+vnoise(wp.xz*.7)*1.2,mainR?6.:4.8,a);
 col=mix(col,grassC,verge*.8);
 // shell holes: the surface opens over the crater so the hole in the ground shows, with a ring of churned earth round it
 float hole=0.,ring=0.;
 for(int i=0;i<24;i++){vec4 H=uHoles[i];if(H.z<=0.)continue;float d=length(vRel.xz-H.xy)/H.z;hole=max(hole,1.-smoothstep(.72,.86,d));ring=max(ring,1.-smoothstep(.86,1.7,d));}
 col=mix(col,mud*.55,ring*.85);
 float rag=vnoise(wp.xz*1.3+s*.05);
 float alpha=1.-smoothstep((mainR?6.:4.8)+rag*.9,mainR?7.7:6.4,a);
 alpha*=(1.-hole)*(1.-smoothstep(uFarR*.7,uFarR,dist));
 float sunUp=smoothstep(-.03,.08,uLightDir.y);
 float ndl=clamp(uLightDir.y,0.,1.)*.92+.08;
 vec3 light=uLightCol*ndl*sunUp*sunShadow(vRel,vec3(0.,1.,0.))+mix(uAmbDown,uAmbUp,.85);
 vec3 res=mix(col*light,fogColor(-V),fogAmount(dist));
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);
 oCol=vec4(res,alpha);
}`;

// ---------------- units: ship, vehicles and soldiers (instanced, vertex colours) ----------------
// moving-part groups a vehicle may have. v5.3: 97 where the graphics chip has room for the bigger uniform arrays (almost all), else 57
const PART_SLOTS=(()=>{try{const g=document.createElement('canvas').getContext('webgl2'),m=g?g.getParameter(g.MAX_VERTEX_UNIFORM_VECTORS):0,x=g&&g.getExtension('WEBGL_lose_context');if(x)x.loseContext();return m>=512?97:57;}catch(e){return 57;}})();
const UNIT_VS=GLSL_HEAD+GLSL_COMMON+`
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNrm;
layout(location=2) in vec4 aCol;      // rgb, part (0 rigid, 1-4 limbs, 7 lights)
layout(location=3) in vec4 aInst;     // x, y, z (relative to the set origin), heading
layout(location=4) in vec4 aInst2;    // pitch, walking (0..1), phase, scale
layout(location=5) in float aGrp;     // moving-part group (stays 0 for every mesh without parts)
uniform vec4 uPA[${PART_SLOTS}];       // per part: pivot xyz, turn angle
uniform vec4 uPB[${PART_SLOTS}];       // per part: turn axis xyz, size about the pivot
uniform vec4 uPC[${PART_SLOTS}];       // per part: slide xyz, the part it rides on
uniform mat4 uVP;
uniform vec2 uOrigRel;
uniform float uRoll;                  // 1 while drawing ships: the walking amount slot then carries the roll angle
out vec3 vRel; out vec3 vN; out vec4 vCol; out vec3 vP; out float vLogW; out float vAlpha; out float vFac;
vec3 rotAxis(vec3 v,vec3 k,float c,float s){return v*c+cross(k,v)*s+k*dot(k,v)*(1.-c);}
void animPart(inout vec3 p,inout vec3 n,int g){
 vec4 A=uPA[g],B=uPB[g];float c=cos(A.w),s=sin(A.w);
 p=A.xyz+rotAxis(p-A.xyz,B.xyz,c,s)*B.w+uPC[g].xyz;n=rotAxis(n,B.xyz,c,s);
}
uniform float uMatte;
uniform float uAI;                    // 1 while drawing AI tanks: groups are wheels, track runs, barrels and flashes; the walking slot carries distance or recoil
void aiPart(inout vec3 p,inout vec3 n,int g){
 vec4 A=uPA[g],B=uPB[g],C=uPC[g];float m=C.w,d=aInst2.y;
 if(m<.5){float a=-d*A.w,c=cos(a),s=sin(a);p=C.xyz+rotAxis(p-C.xyz,B.xyz,c,s);n=rotAxis(n,B.xyz,c,s);}
 else if(m<2.5)p.x+=(m<1.5?1.:-1.)*mod(d,A.w);
 else if(m<3.5)p+=B.xyz*A.w*d;
 else p=C.xyz+(p-C.xyz)*step(.55,d);
}
void main(){
 vec3 p=aPos,n=aNrm;float part=aCol.w;vAlpha=aInst2.y;
 int grp=int(aGrp+.5);
 if(grp>0){if(uAI>.5)aiPart(p,n,grp);else{animPart(p,n,grp);int up=int(uPC[grp].w+.5);if(up>0)animPart(p,n,up);}}      // a barrel turns with its turret
 if(part>5.9&&part<6.1){                                         // bird wings: bursts of flapping between long glides, a little dihedral while gliding
  float ph=aInst2.z,gl=smoothstep(-.1,.5,sin(uTime*.45+ph*3.7));
  float th=(.12+.62*sin(uTime*(8.5+fract(ph)*2.)+ph*6.)*gl)*sign(p.z),c=cos(th),s=sin(th);
  p=vec3(p.x,p.y*c+p.z*s,p.z*c-p.y*s);n=vec3(n.x,n.y*c+n.z*s,n.z*c-n.y*s);
 }
 if(uRoll>.5){float cr=cos(aInst2.y),sr=sin(aInst2.y);p=vec3(p.x,p.y*cr-p.z*sr,p.y*sr+p.z*cr);n=vec3(n.x,n.y*cr-n.z*sr,n.y*sr+n.z*cr);}
 if(part>.5&&part<4.5&&aInst2.y>.01){                             // soldiers swing legs and arms while walking
  float pivot=part<2.5?.92:1.42,sgn=(part<1.5||part>3.5)?1.:-1.;
  float a=sin(uTime*7.+aInst2.z)*.62*aInst2.y*sgn,c=cos(a),s=sin(a),dy=p.y-pivot;
  p=vec3(p.x*c-dy*s,pivot+p.x*s+dy*c,p.z);n=vec3(n.x*c-n.y*s,n.x*s+n.y*c,n.z);
 }
 if(uMatte>.5){                                                   // v4.9 plants sway in the wind, leaves flutter
  float hy=max(p.y,0.),ph=uTime*.7+aInst.x*.013+aInst.z*.011,a=hy*hy*.00009;
  p.x+=sin(ph)*a;p.z+=cos(ph*.83)*a*.7;
  if(part>1.9)p.y+=sin(uTime*2.6+p.x*.9+p.z*.7+ph)*.05*min(hy*.1,1.);
 }
 p*=aInst2.w;
 float cp=cos(aInst2.x),sp=sin(aInst2.x);
 p=vec3(p.x*cp-p.y*sp,p.x*sp+p.y*cp,p.z);n=vec3(n.x*cp-n.y*sp,n.x*sp+n.y*cp,n.z);
 float ch=cos(aInst.w),sh=sin(aInst.w);
 p=vec3(ch*p.x+sh*p.z,p.y,-sh*p.x+ch*p.z);n=vec3(ch*n.x+sh*n.z,n.y,-sh*n.x+ch*n.z);
 vRel=vec3(uOrigRel.x+aInst.x+p.x,aInst.y-uCam.y+p.y,uOrigRel.y+aInst.z+p.z);
 vN=n;vCol=aCol;vP=aPos;vFac=aInst2.z;
 vec4 clip=uVP*vec4(vRel,1.);vLogW=1.+clip.w;gl_Position=clip;
}`;
const UNIT_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec3 vN; in vec4 vCol; in vec3 vP; in float vLogW; in float vAlpha; in float vFac;
out vec4 oCol;
const vec3 FACCOL[5]=vec3[5](vec3(.5),vec3(.16,.42,.80),vec3(.20,.60,.28),vec3(.78,.14,.12),vec3(.86,.64,.10));
uniform float uMatte;                  // v4.9 1 for plants: bark and leaf shading
uniform float uDet;                    // 1 for ships and vehicles: plating, weathering and reflections; 0 for soldiers, shells and sparks
uniform float uVType;                  // 0 other, 1 warship, 2 land vehicle, 3 aircraft: picks the camouflage scheme
uniform float uDmg;                    // 0..1 damage of the player's vehicle: soot, rust and glowing embers
uniform float uSoft;                   // v3.7 1 for dust: a soft, translucent puff that fades at its edges instead of a solid lump
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 if(uSoft>1.5){                         // v3.8 fireball: hot white-yellow core fading to orange at the edge, glowing, see-through as it dies
  vec3 N=normalize(vN);float ed=abs(dot(N,V));
  float nz=vnoise3(vP*3.3+vec3(0.,uTime*1.4,0.));
  float nz2=vnoise3(vP*7.1-vec3(0.,uTime*2.,0.));
  float a=vAlpha*smoothstep(.12,.85,ed)*clamp(.15+.9*nz+.35*nz2-.25*(1.-vAlpha),0.,1.);
  float core=smoothstep(.55,1.,ed)*vAlpha;
  vec3 hot=mix(vec3(.9,.24,.04),vec3(1.,.66,.28),core+nz2*.25)*(.9+1.6*core);
  vec3 dc=mix(hot,vec3(.09,.08,.07),smoothstep(.6,.05,vAlpha)*.85);
  dc=mix(dc,fogColor(-V),fogAmount(dist));
  gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);oCol=vec4(dc,clamp(a,0.,1.));return;
 }
 if(uSoft>.5){
  vec3 N=normalize(vN);float ed=abs(dot(N,V));
  float a=vAlpha*smoothstep(.05,.75,ed)*(.55+.6*vnoise3(vP*2.1+vec3(0.,uTime*.25,0.)));
  vec3 base=vFac>1.5?lin(vec3(.9,.93,.95)):lin(vCol.rgb)*(vFac>.01?vFac:1.);   // v4.9 smoke carries its own shade (black fires, grey funnels); above 1.5 it is white spray and mist
  vec3 dc=base*(uLightCol*(max(dot(N,uLightDir),0.)*.55+.45)*max(uLightDir.y+.15,.2)+mix(uAmbDown,uAmbUp,N.y*.5+.5)*1.15);
  dc=mix(dc,fogColor(-V),fogAmount(dist));
  gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);oCol=vec4(dc,clamp(a,0.,1.));return;
 }
 if(vCol.w>8.5){                                                    // decals: bullet holes, chips and scorch on a surface, translucent
  float r=length(vP.xz)*2.,ty=floor(vFac+.001),sd=fract(vFac)*37.,ang=atan(vP.z,vP.x);
  float wob=vnoise(vec2(ang*2.3+sd,sd*1.7))*.5+vnoise(vec2(ang*5.1-sd,sd))*.25;
  vec3 N=normalize(vN);if(dot(N,V)<0.)N=-N;
  vec3 base;float a;
  if(ty<2.5){                                                          // a hole: black core inside a ring of kicked-up chips (earth, splinters or flakes)
   float rr=r*(1.+(wob-.38)*.55);
   vec3 chip=ty<.5?lin(vec3(.30,.22,.14)):ty<1.5?lin(vec3(.62,.46,.28)):lin(vec3(.55,.55,.55));
   float core=1.-smoothstep(.26,.40,rr),ring=smoothstep(.34,.55,rr)*(1.-smoothstep(.55,1.,rr));
   base=mix(chip*.8,vec3(.012),core);a=max(core*.96,ring*.42);
  }else{                                                               // scorch: a sooty blotch with streaks thrown outwards
   float st=vnoise(vec2(ang*3.+sd,sd*2.1));
   float k=1.-smoothstep(.12,1.,r*(1.+.55*(st-.5)));
   base=lin(vec3(.02,.018,.016));a=k*.85*(.65+.35*vnoise(vP.xz*6.+sd));
  }
  float ndl=max(dot(N,uLightDir),0.)*smoothstep(-.03,.08,uLightDir.y);
  vec3 dc=base*(uLightCol*ndl+mix(uAmbDown,uAmbUp,N.y*.5+.5));
  dc=mix(dc,fogColor(-V),fogAmount(dist));
  gl_FragDepth=clamp(log2(max(1.,vLogW-(.4+dist*.012)))*uFcoef*.5,0.,1.);oCol=vec4(dc,clamp(a*vAlpha,0.,1.));return;     // pulled a little towards the viewer so a mark on a slope or a faceted trunk is not buried
 }
 if(vCol.w>7.5&&vCol.w<8.5){                                                    // wake foam: a soft white disc that fades out
  float r=length(vP.xz),a=vAlpha*(1.-smoothstep(.3,1.,r))*(.55+.6*vnoise3(vec3(vRel.xz+uCam.xz,uTime*.3).xzy*.35));
  vec3 fc=mix(lin(vec3(.85,.93,.95))*(uAmbUp*1.3+uLightCol*max(uLightDir.y,0.)*.5),fogColor(-V),fogAmount(dist));
  gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);oCol=vec4(fc,clamp(a,0.,1.));return;
 }
 vec3 N=normalize(vN);if(dot(N,V)<0.)N=-N;
 vec3 wp=vRel+uCam;
 vec3 col=lin(vCol.rgb);
 if(uMatte>.5){                                                     // v4.9 plants: furrowed mossy bark; leaves with a midrib, mottling and light shining through
  float pc=vCol.w,trans=0.,occ=1.,shine=.03,nd=1.-smoothstep(60.,420.,dist);
  vec3 P=vP;
  if(pc<1.5){
   float fur=vnoise3(P*vec3(1.4,.16,1.4)+7.);
   col*=.5+.8*fur;
   float moss=smoothstep(.45,.9,N.y*.55+fur*.5+(1.-smoothstep(0.,8.,P.y))*.3);
   col=mix(col,lin(vec3(.09,.21,.13)),moss*.8);
   if(nd>0.){float g=vnoise3(P*vec3(2.6,.3,2.6));N=normalize(N+vec3(g-.5,0.,.5-g)*1.1*nd);}
   occ=.45+.55*smoothstep(-2.,10.,P.y);
  }else{
   {float eg=1.-abs(dot(N,V)),rn=vnoise3(wp*.9)*.6+vnoise3(wp*2.6)*.4;                // v5.3 ragged leaf edges
    if(dist<500.&&rn<(eg-.45)*1.8*(1.-smoothstep(250.,500.,dist)))discard;}
   float ac=fract(pc),mid=1.-smoothstep(.0,.05,abs(ac-.5)),edge=smoothstep(.36,.49,abs(ac-.5));
   float var=vnoise3(P*.6+col*17.);
   col*=.7+.6*var;
   col=mix(col,col*1.7+lin(vec3(.02,.05,.03)),mid*.55*nd);
   col=mix(col,col*.6,edge*.45);
   if(pc>2.9)col*=1.25;
   trans=1.;shine=.14;
   occ=mix(.5,1.,smoothstep(-.7,.6,N.y));
   if(pc>2.2&&pc<2.3){                                            // the dense mass of a crown: clumps of leaves with dark gaps between
    float cl=vnoise3(P*.5+col*3.),cl2=vnoise3(P*1.6+3.);
    N=normalize(N+vec3(cl-.5,cl2-.5,cl2-cl)*2.4);
    col*=.4+.8*(cl*.6+cl2*.4);occ*=.5+.6*smoothstep(.3,.7,cl);shine=.02;trans=.4;
   }
  }
  float ndl=dot(N,uLightDir),sunU=smoothstep(-.03,.08,uLightDir.y);
  float sunSh=sunShadow(vRel,N);
  vec3 Lt=uLightCol*max(ndl,0.)*sunU*occ*sunSh+mix(uAmbDown,uAmbUp,N.y*.5+.5)*occ*1.05;
  Lt+=trans*uLightCol*lin(vec3(.5,.85,.55))*max(-ndl,0.)*.5*sunU;
  Lt+=trans*uLightCol*pow(max(dot(-V,uLightDir),0.),4.)*.3*sunU;
  vec3 Hh=normalize(uLightDir+V);
  vec3 res=col*Lt+uLightCol*pow(max(dot(N,Hh),0.),36.)*shine*sunU*occ;
  res=mix(res,fogColor(-V),fogAmount(dist));
  gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);oCol=vec4(res,1.);return;
 }
 if(vCol.w>4.5&&vCol.w<5.5){int fi=int(vFac+.5);if(fi>0&&fi<5)col=lin(FACCOL[fi]*.78);}      // hull paint in the faction colour
 float grain=vnoise3(vP*vec3(2.,2.,2.)*(dist<80.?3.:1.)+vCol.rgb*7.);        // paint and metal are never perfectly even
 col*=.86+.28*grain;
 float lum=dot(col,vec3(.3,.59,.11)),wy=vRel.y+uCam.y;
 float fineK=uDet*(1.-smoothstep(140.,620.,dist));
 vec3 nl=normalize(cross(dFdx(vP),dFdy(vP)));                          // flat object-space normal: decides how plating is laid out
 float camoK=uVType>.5&&uDet>.5&&vCol.w<5.5&&lum>.035&&lum<.62?1.-smoothstep(260.,900.,dist):0.;   // paint only: lamps, glass, tracks and bright trim keep their colour
 if(camoK>0.){
  if(uVType<1.5){
   // warships: WW1 dazzle - hard-edged diagonal bands that break up the hull's lines
   float bw=vP.x*.055+vP.y*.11*sign(vP.z+.001)+.35*vnoise3(vP*.018);
   float bd=fract(bw),b2=fract(vP.x*.031-vP.y*.07+.5*vnoise3(vP*.013+5.));
   float side=1.-smoothstep(.55,.8,abs(nl.y));
   vec3 dk=col*vec3(.46,.48,.52),lt=mix(col,vec3(.62,.66,.68),.45);
   vec3 dz=bd<.32?dk:bd<.5?lt:col;dz=b2<.1?mix(dz,dk,.7):dz;
   col=mix(col,dz,side*camoK*.85);
  }else if(uVType<2.5){
   // land vehicles: three-tone disruptive blotches, mud kicked up the lower hull, dust settled on top
   vec3 q=vP*.42+vec3(vFac*3.7);
   float n1=vnoise3(q)+.5*vnoise3(q*2.3+7.),n2=vnoise3(q*.8+13.)+.5*vnoise3(q*1.9+3.);
   vec3 brown=col*vec3(.72,.55,.38),blk=col*vec3(.32,.30,.27),lt=col*vec3(1.07,1.06,.92);
   vec3 cm=n1>.66?brown:n1<.2?lt:col;cm=n2>.86?blk:cm;
   col=mix(col,cm,camoK);
   float mud=smoothstep(1.3,.15,vP.y)*(.55+.45*vnoise3(vP*2.1));
   col=mix(col,lin(vec3(.30,.24,.16)),clamp(mud,0.,1.)*.75*camoK);
   if(nl.y>.7)col=mix(col,lin(vec3(.52,.46,.36)),.22*vnoise3(vP*1.4+2.)*camoK);
   col*=1.-.18*smoothstep(.55,.95,vnoise3(vec3(vP.x*1.7,vP.y*.25,vP.z*1.7)))*camoK*(1.-abs(nl.y));   // grime streaks
  }else{
   // aircraft: a soft two-tone pattern on top, pale counter-shaded belly
   float n1=vnoise3(vP*.16+vec3(vFac*2.1))+.4*vnoise3(vP*.45);
   col=mix(col,col*vec3(.70,.74,.72),smoothstep(.6,.72,n1)*camoK*step(-.2,nl.y));
   col=mix(col,max(col,lin(vec3(.62,.66,.70))),smoothstep(-.2,-.7,nl.y)*camoK);
   col*=1.-.12*smoothstep(.6,.9,vnoise3(vP*vec3(.9,.2,.9)+4.))*camoK;   // exhaust and oil staining
  }
 }
 if(uDet>.5&&vCol.w<6.5){
  // surface character: plating seams, weld streaks, anti-slip decks, a dirty waterline
  vec2 uv=abs(nl.y)>.7?vP.xz:abs(nl.x)>.7?vP.zy:vP.xy;
  vec2 f=abs(fract(uv/3.4)-.5);
  col*=1.-.20*smoothstep(.46,.5,max(f.x,f.y))*fineK;                             // plate seams
  col*=1.-.22*smoothstep(.5,.85,vnoise3(vec3(vP.x*1.3,vP.y*.14,vP.z*1.3)))*fineK*(1.-abs(nl.y));   // rain and rust streaks running down the sides
  if(nl.y>.7)col*=.84+.3*vnoise3(vec3(vP.x*.9,vP.y,vP.z*5.))*fineK+.06*(1.-fineK);   // deck: non-slip grain and scuffs
  float isSea=uVType<1.5?1.:0.;
  col=mix(col,lin(vec3(.30,.07,.05)),smoothstep(.5,-.1,wy)*uDet*isSea);   // red anti-fouling paint below the waterline
  col*=1.-.38*smoothstep(1.6,.2,wy)*uDet*isSea;                                          // wet hull
 }
 // damage: soot blooms, rust, and glowing embers once the vehicle is burning
 if(uDmg>.02&&vCol.w<6.5){
  float n1=vnoise3(vP*.32+vec3(3.1,1.7,5.2)),n2=vnoise3(vP*1.3+vec3(8.,2.,1.));
  float soot=smoothstep(.62-uDmg*.4,.78,n1)*clamp(uDmg*1.6,0.,1.);
  col=mix(col,lin(vec3(.035,.03,.03)),soot*.85);
  col=mix(col,lin(vec3(.35,.14,.06)),smoothstep(.55,.8,n2)*uDmg*.5*(1.-soot));
 }
 float sunUp=smoothstep(-.03,.08,uLightDir.y);
 float ndl=max(dot(N,uLightDir),0.);
 float sky=N.y*.5+.5;
 float sunSh=sunShadow(vRel,N);
 vec3 light=uLightCol*ndl*sunUp*sunSh+mix(uAmbDown,uAmbUp,sky)*(.7+.3*sky)*mix(.75,1.,sunSh);
 float ndv=max(dot(N,V),0.),fr=.04+.96*pow(1.-ndv,5.);
 vec3 H=normalize(uLightDir+V);
 float nh=max(dot(N,H),0.);
 vec3 spec=uLightCol*(pow(nh,28.)*.10+pow(nh,140.)*.45)*sunUp*sunSh*(.4+.6*smoothstep(.45,.0,lum));
 vec3 res=col*light+spec;
 if(uDet>.5&&vCol.w<6.5){
  // the sky and the sea in the paint: grazing angles and dark glassy surfaces mirror their surroundings
  vec3 Rf=reflect(-V,N);
  vec3 env=Rf.y>0.?skyBase(Rf):mix(lin(vec3(.05,.17,.21))*(.35+uAmbUp),skyBase(normalize(vec3(Rf.x,.03,Rf.z))),.22);
  float rk=mix(.60,.07,smoothstep(.02,.22,lum))*(1.-.55*smoothstep(1.6,.2,wy))*(abs(uVType-2.)<.5?.3:1.);   // matt land vehicles barely mirror the sky
  res=mix(res,env,clamp(rk*(.14+fr),0.,.85)*fineK);
  res+=col*uAmbUp*pow(1.-ndv,3.)*.2*fineK;                                       // rim light keeps the silhouette readable against the sky
 }
 if(uDmg>.7&&vCol.w<6.5){res+=vec3(1.,.38,.06)*smoothstep(.72,.9,vnoise3(vP*1.1+vec3(uTime*.35,0.,uTime*.2)))*(uDmg-.7)*3.2;}   // embers
 if(vCol.w>6.5&&vCol.w<7.5){float bl=fract(vFac)>.01?.12+.88*step(.7,fract(uTime*.5+fract(vFac)*7.)):1.;res=col*(1.5+2.*uNight)*bl;}   // running lights and windows; a fractional phase makes a light flash (buoys)
 res=mix(res,fogColor(-V),fogAmount(dist));
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);
 oCol=vec4(res,1.);
}`;

// ---------------- water ----------------
const WATER_VS=GLSL_HEAD+GLSL_COMMON+`
in vec2 aPos;                 // metres around the camera
uniform vec2 uCenterRel;      // the mesh centre relative to the camera (xz)
uniform vec2 uCenterWorld;    // the mesh centre in world space (xz)
uniform mat4 uVP;
uniform float uWind;
uniform vec3 uShel[4];         // calm water inside harbours: centre xz and radius
uniform vec4 uShip[8];         // v4.3 hulls pushing the water aside (90_sea.js)
uniform sampler2D uShore;      // swell factor by depth around the camera (04_shore.js): 0 on and above the shore, 1 in deep water
uniform vec3 uShoreO;          // grid origin xz and 1 / extent
out vec3 vRel; out vec3 vN; out float vCrest; out vec2 vW; out float vLogW; out float vSh;
float shoreK(vec2 w){
 vec2 uv=(w-uShoreO.xy)*uShoreO.z;
 if(uv.x<=0.||uv.y<=0.||uv.x>=1.||uv.y>=1.)return 1.;
 vec2 e=min(uv,1.-uv);float f=clamp(min(e.x,e.y)/.03,0.,1.);
 return mix(1.,texture(uShore,uv).r,f*f*(3.-2.*f));
}
const int NW=7;
float sq(float x){return x*x;}
float shipWake(vec2 p,float spacing){float H=0.;
 for(int j=0;j<4;j++){vec4 a=uShip[j*2],b=uShip[j*2+1];if(a.w<=0.)continue;
  vec2 d=p-a.xy;float L=a.w,hb=b.x*.5,v=b.y,dr=b.z;if(dot(d,d)>sq(L*2.5+250.))continue;
  vec2 f=vec2(cos(a.z),-sin(a.z))*b.w;float u=dot(d,f),w=abs(dot(d,vec2(-f.y,f.x)));
  float fr=v*v/9.81,amp=min(.035*fr,dr*.2+.3)+.03*dr;          // the bow wave grows with the square of the speed; a laden hull shoulders more water
  float t=clamp(u/(L*.5),-1.,1.),hw=hb*sqrt(max(0.,1.-sq(max(0.,abs(t)-.35)/.65))),ou=w-hw;
  float sb=L*.5-u,crest=hb*.6+max(0.,sb)*.354,wd=max(1.5,hb*.5)+max(0.,sb)*.03,h=0.;
  // the bow wave: a hump at the stem and a crest running aft at the Kelvin angle
  h+=amp*exp(-sq((w-crest)/wd))*exp(-max(0.,sb)/(L*.6+30.))*smoothstep(-hb*2.,0.,sb)*step(0.,ou+wd*.3);
  // along the hull: piled up at the forward shoulder, drawn down amidships and aft
  if(abs(u)<L*.55&&ou>0.){float side=exp(-sq(ou/(hb*.8+1.)));h+=amp*.8*side*(.7*smoothstep(0.,.6,t)-.55*(1.-smoothstep(-.9,.2,t))*smoothstep(-1.1,-.8,t));}
  // astern: the transverse waves of the wake inside the wedge, and the hollow the hull leaves behind it
  float sa=-L*.5-u;
  if(sa>0.&&v>1.){float lam=max(4.,6.2832*fr),wg=hb+sa*.354;h+=amp*.45*sin(6.2832*sa/lam)*exp(-sa/(L*.8+40.))*smoothstep(wg,wg*.6,w);
   h-=amp*.3*exp(-sq(w/(hb+sa*.05)))*exp(-sa/(L*.6+20.));}
  H+=h*smoothstep(0.,1.,(hb+2.)/spacing);}
 return H;}
void main(){
 vec2 wxz=uCenterWorld+aPos;
 float r=length(aPos);
 float spacing=max(.8,r*.045);
 vec3 P=vec3(0.);vec3 dN=vec3(0.,1.,0.);float jac=0.;
 // wavelength, amplitude at full sea; mirrored by WAVES in 04_weather.js (the ships ride this swell)
 float L[NW];float A[NW];
 L[0]=210.;L[1]=120.;L[2]=70.;L[3]=40.;L[4]=22.;L[5]=12.;L[6]=6.5;
 A[0]=5.6;A[1]=4.;A[2]=2.4;A[3]=1.1;A[4]=.6;A[5]=.3;A[6]=.15;
 float sh=0.;
 for(int j=0;j<4;j++){if(uShel[j].z>0.){float dd=length(wxz-uShel[j].xy);sh=max(sh,1.-smoothstep(uShel[j].z*.55,uShel[j].z,dd));}}
 float gain=(.3+.7*pow(clamp(uWind,0.,1.),1.6))*(1.-.65*sh)*shoreK(wxz);
 for(int i=0;i<NW;i++){
  float fi=float(i);
  float ang=.45+fi*.83+.6*sin(fi*2.1);
  vec2 dir=vec2(cos(ang),sin(ang));
  float k=6.2831853/L[i];
  float c=sqrt(9.81/k);
  float fade=smoothstep(2.,7.,L[i]/spacing);
  float amp=min(A[i]*gain,L[i]*.05)*fade;
  float ph=k*dot(dir,wxz)-c*k*uTime;
  float sn=sin(ph),cs=cos(ph);
  float q=.62/(k*max(amp,.001)*float(NW)/1.5+.001);
  q=min(q,1.1);
  P.xz+=dir*(q*amp*cs);
  P.y+=amp*sn;
  dN.xz-=dir*(k*amp*cs);
  dN.y-=q*k*amp*sn;
  jac+=q*k*amp*sn;
 }
 {float s0=shipWake(wxz,spacing);if(s0!=0.){float sx=shipWake(wxz+vec2(.7,0.),spacing),sz=shipWake(wxz+vec2(0.,.7),spacing);P.y+=s0;dN.x-=(sx-s0)/.7;dN.z-=(sz-s0)/.7;jac+=max(0.,s0-.25)*.18;}}
 vec3 N=normalize(vec3(dN.x*2.3,max(dN.y,.2),dN.z*2.3));   // slopes exaggerated a little so the swell is readable from far away
 vRel=vec3(uCenterRel.x+aPos.x+P.x,P.y-uCam.y,uCenterRel.y+aPos.y+P.z);
 vN=N;vCrest=jac;vW=wxz;vSh=sh;
 vec4 clip=uVP*vec4(vRel,1.);vLogW=1.+clip.w;gl_Position=clip;
}`;
const WATER_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel; in vec3 vN; in float vCrest; in vec2 vW; in float vLogW; in float vSh;
uniform float uWind;
uniform float uRain;
out vec4 oCol;
void main(){
 float dist=length(vRel);
 vec3 V=-vRel/dist;
 vec3 N=normalize(vN);
 // small ripples on top of the big waves, fading with distance
 float rf=1.-smoothstep(60.,900.,dist);
 vec2 p1=vW*.85+vec2(uTime*.6,uTime*.35),p2=vW*2.3-vec2(uTime*.5,-uTime*.45),p3=vW*6.1+vec2(uTime*.9,-uTime*.7);
 float e=.08;
 float n1=vnoise(p1),n2=vnoise(p2),n3=vnoise(p3);
 vec2 gr=vec2(vnoise(p1+vec2(e,0.))-n1,vnoise(p1+vec2(0.,e))-n1)/e*.05
        +vec2(vnoise(p2+vec2(e,0.))-n2,vnoise(p2+vec2(0.,e))-n2)/e*.03
        +vec2(vnoise(p3+vec2(e,0.))-n3,vnoise(p3+vec2(0.,e))-n3)/e*.015;
 // broader chop that stays visible out to the horizon, so the sea breaks up the reflected sky instead of mirroring it flat
 vec2 p0=vW*.11+vec2(uTime*.35,-uTime*.2);float n0=vnoise(p0);
 vec2 g0=vec2(vnoise(p0+vec2(.1,0.))-n0,vnoise(p0+vec2(0.,.1))-n0)/.1*.075*(.5+uWind);
 N=normalize(N+vec3(gr.x,0.,gr.y)*rf*(.6+uWind)+vec3(g0.x,0.,g0.y)*(1.-smoothstep(2500.,7000.,dist)));
 // rain pocks the surface with rings
 if(uRain>.01){
  vec2 rp=vW*.55;vec2 id=floor(rp),f=fract(rp)-.5;
  float hh=hash12(id),ph=fract(uTime*(.8+hh*.5)+hh*7.);
  vec2 off=(vec2(hash12(id+3.1),hash12(id+8.7))-.5)*.5;
  float d=length(f-off),ring=smoothstep(.07,.0,abs(d-ph*.55))*(1.-ph)*step(hh,uRain*.8);
  N=normalize(N+vec3(normalize(f-off+1e-4)*ring*.5,0.).xzy*(1.-smoothstep(40.,260.,dist)));
 }
 float ndv=clamp(dot(N,V),0.,1.);
 float fres=.02+.98*pow(clamp(1.-ndv,0.,1.),5.);
 vec3 R=reflect(-V,N);R.y=abs(R.y);
 vec3 refl=skyBase(normalize(R));
 // the sun and its glitter path
 vec3 Hh=normalize(uLightDir+V);
 float nh=max(dot(N,Hh),0.);
 vec3 spec=uLightCol*(pow(nh,900.)*28.+pow(nh,140.)*1.4+pow(nh,18.)*.08)*smoothstep(-.02,.06,uLightDir.y);
 spec=spec/(1.+spec*.22);
 // body colour: the open sea shifts between teal and navy over long distances, waves facing the sun glow, crests let light through
 float patchN=vnoise(vW*.0005+3.)*.6+vnoise(vW*.0021+9.)*.4;
 vec3 deep=mix(lin(vec3(.004,.075,.19)),lin(vec3(.008,.15,.25)),patchN),turq=mix(lin(vec3(.02,.36,.38)),lin(vec3(.04,.46,.40)),patchN);
 float crestK=clamp(vCrest*1.2+.1,0.,1.);
 float face=pow(clamp(dot(N,uLightDir)*.5+.5,0.,1.),2.2);          // slopes turned towards the sun are brighter, so the swell reads
 vec3 body=mix(deep,turq,crestK*.75+.1+face*.25);
 float sun=max(uLightDir.y,0.);
 float sss=pow(max(dot(V,-uLightDir)*.5+.5,0.),4.)*smoothstep(0.,.5,vCrest+.2)*sun;
 body=body*(uAmbUp*1.1+uLightCol*sun*(.05+.9*face))+turq*uLightCol*sss*.45;
 refl*=mix(vec3(1.),lin(vec3(.80,.92,1.)),.35)*.82;
 vec3 col=mix(body,refl,fres*.92)+spec;
 // foam on the crests, torn by noise
 float fn=vnoise(vW*1.1+uTime*.2)*.45+vnoise(vW*3.7-uTime*.3)*.33+vnoise(vW*10.+uTime*.1)*.22;
 float far=1.-smoothstep(500.,2600.,dist);
 float foam=smoothstep(.0,.3,vCrest+uWind*.18-vSh*.6-.52+(fn-.5)*1.0)*far;
 vec2 wd=vec2(.9,.435),wp=vec2(-.435,.9);
 float streak=smoothstep(.6,.85,vnoise(vec2(dot(vW,wd)*.012,dot(vW,wp)*.33)+uTime*.03))*smoothstep(.5,.95,uWind)*(1.-smoothstep(300.,2200.,dist))*(1.-vSh);   // wind-blown streaks along the sea
 foam=max(foam,streak*.5*smoothstep(.35,.7,fn));
 col=mix(col,(uAmbUp*1.5+uLightCol*.5*max(uLightDir.y,.1))*vec3(.95,1.,1.),foam*.7);
 float fa=fogAmount(dist)*.7;
 col=mix(col,fogColor(-V),fa);
 float alpha=mix(.92,1.,smoothstep(0.,3500.,dist));
 alpha=mix(alpha,1.,max(fres*.7,fa));
 gl_FragDepth=clamp(log2(vLogW)*uFcoef*.5,0.,1.);
 if(isnan(col.r)||isnan(col.g)||isnan(col.b))col=vec3(.02,.2,.3);       // a stray NaN would otherwise smear through the bloom and blank the sea
 if(isnan(alpha))alpha=1.;
 oCol=vec4(clamp(col,0.,60.),clamp(alpha,0.,1.));
}`;
// the simple sea: a flat sheet with cheap ripples, depth written by the vertex stage - the last resort for graphics drivers that choke on the full ocean
const WATER_C_VS=GLSL_HEAD+GLSL_COMMON+`
in vec2 aPos;
uniform vec2 uCenterRel;
uniform mat4 uVP;
out vec3 vRel;
void main(){
 vRel=vec3(uCenterRel.x+aPos.x,-uCam.y,uCenterRel.y+aPos.y);
 gl_Position=logDepth(uVP*vec4(vRel,1.));
}`;
const WATER_C_FS=GLSL_HEAD+GLSL_COMMON+`
in vec3 vRel;
out vec4 oCol;
void main(){
 float dist=max(length(vRel),1.);
 vec3 V=-vRel/dist;
 vec2 w=vRel.xz+uCam.xz;
 float rf=1.-smoothstep(200.,2500.,dist);
 vec3 N=normalize(vec3((.07*sin(w.x*.21+uTime*1.3)+.045*sin(w.y*.33-uTime)+.02*sin(w.x*.9+w.y*.7+uTime*2.))*rf,1.,(.07*sin(w.y*.17+uTime*1.1)+.045*sin(w.x*.41+uTime*.7)+.02*sin(w.y*.8-w.x*.6+uTime*1.7))*rf));
 float ndv=clamp(dot(N,V),0.,1.);
 float fres=.03+.97*pow(clamp(1.-ndv,0.,1.),4.);
 vec3 R=reflect(-V,N);R.y=abs(R.y);
 vec3 refl=skyBase(normalize(R));
 float face=clamp(dot(N,uLightDir)*.5+.5,0.,1.);
 vec3 body=mix(lin(vec3(.006,.10,.21)),lin(vec3(.03,.30,.34)),.25+.4*face)*(uAmbUp*1.1+uLightCol*max(uLightDir.y,0.)*(.1+.6*face));
 vec3 Hh=normalize(uLightDir+V);
 vec3 spec=uLightCol*pow(max(dot(N,Hh),0.),120.)*1.2*smoothstep(-.02,.06,uLightDir.y);
 vec3 col=mix(body,refl*.85,fres)+spec;
 col=mix(col,fogColor(-V),fogAmount(dist)*.7);
 if(isnan(col.r)||isnan(col.g)||isnan(col.b))col=vec3(.02,.2,.3);
 oCol=vec4(clamp(col,0.,60.),1.);
}`;

// ---------------- rain: thousands of short streaks in a box that travels with the camera ----------------
// Each drop has a fixed spot in a 70 m box tiled through the world, so drops stay put as the camera moves, fall past objects and hide behind them.
const RAIN_VS=GLSL_HEAD+GLSL_COMMON+`
uniform mat4 uVP; uniform vec3 uFall; uniform vec4 uLayer;   // v3.7 box size, fade start, fade end, streak length
out float vA;
void main(){
 int id=gl_VertexID>>1;float fi=float(id),end=float(gl_VertexID&1);
 vec3 h=vec3(hash12(vec2(fi,1.7)),hash12(vec2(fi,7.3)),hash12(vec2(fi,13.1)));
 float S=uLayer.x;
 vec3 rel=mod(h*S-uCam-uFall*uTime*(.85+.3*hash12(vec2(fi,3.3))),S)-S*.5;
 rel-=normalize(uFall)*end*(.9+.5*h.x)*uLayer.w;
 float d=length(rel);
 vA=(1.-smoothstep(uLayer.y,uLayer.z,d))*smoothstep(.8,2.5,d)*(.45+.55*h.y)*(1.-end*.75);   // drops vary, and each streak thins to its tail
 gl_Position=logDepth(uVP*vec4(rel,1.));
}`;
const RAIN_FS=GLSL_HEAD+GLSL_COMMON+`
in float vA; out vec4 oCol;
void main(){oCol=vec4(uAmbUp*1.6+uLightCol*.14+vec3(.04),vA*.4);}`;
// ---------------- post: bloom + tone mapping ----------------
const POST_VS=GLSL_HEAD+`
out vec2 vUV;
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);vUV=p;gl_Position=vec4(p*2.-1.,0.,1.);}`;
const BLOOM_DOWN_FS=GLSL_HEAD+`
in vec2 vUV;uniform sampler2D uTex;uniform vec2 uTexel;uniform float uFirst;out vec4 oCol;
vec3 samp(vec2 uv){return texture(uTex,uv).rgb;}
void main(){
 vec3 c=samp(vUV)*.25+samp(vUV+uTexel*vec2(1.,1.))*.125+samp(vUV+uTexel*vec2(-1.,1.))*.125+samp(vUV+uTexel*vec2(1.,-1.))*.125+samp(vUV+uTexel*vec2(-1.,-1.))*.125
  +samp(vUV+uTexel*vec2(2.,0.))*.0625+samp(vUV+uTexel*vec2(-2.,0.))*.0625+samp(vUV+uTexel*vec2(0.,2.))*.0625+samp(vUV+uTexel*vec2(0.,-2.))*.0625;
 if(uFirst>.5){float l=max(c.r,max(c.g,c.b));c*=smoothstep(2.4,6.,l);}   // only bright things glow
 oCol=vec4(c,1.);
}`;
const BLOOM_UP_FS=GLSL_HEAD+`
in vec2 vUV;uniform sampler2D uTex;uniform vec2 uTexel;out vec4 oCol;
void main(){
 vec3 c=texture(uTex,vUV+uTexel*vec2(-1.,-1.)).rgb+texture(uTex,vUV+uTexel*vec2(1.,-1.)).rgb+texture(uTex,vUV+uTexel*vec2(-1.,1.)).rgb+texture(uTex,vUV+uTexel*vec2(1.,1.)).rgb
  +2.*(texture(uTex,vUV+uTexel*vec2(0.,-1.)).rgb+texture(uTex,vUV+uTexel*vec2(0.,1.)).rgb+texture(uTex,vUV+uTexel*vec2(-1.,0.)).rgb+texture(uTex,vUV+uTexel*vec2(1.,0.)).rgb)
  +4.*texture(uTex,vUV).rgb;
 oCol=vec4(c/16.,1.);
}`;
const FINAL_FS=GLSL_HEAD+`
in vec2 vUV;uniform sampler2D uScene;uniform sampler2D uBloom;uniform float uExposure;uniform float uBloomK;uniform vec2 uRes;uniform float uFxaa;uniform float uRain;uniform float uRainK;uniform float uTime;out vec4 oCol;
uniform float uSharp;                 // 0 off .. 1 strong: contrast-adaptive sharpening (crisp edges without halos)
uniform vec4 uLook;                   // picture style: vignette, saturation, contrast, warmth
vec3 aces(vec3 x){return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.);}
float hash(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
vec3 cmp(vec3 c){return c/(1.+max(max(c.r,c.g),c.b));}          // compress so a bright pixel cannot swamp its neighbours
vec3 unc(vec3 c){return c/(1.-max(max(c.r,c.g),c.b)+1e-4);}
vec3 tap(vec2 uv){return cmp(texture(uScene,uv).rgb);}
float lum(vec3 c){return dot(c,vec3(.299,.587,.114));}
// a small FXAA: find the local edge direction and blur along it, only where there is contrast
vec3 scene(vec2 uv){
 vec2 px=1./uRes;
 vec3 m=tap(uv);
 if(uFxaa<.5)return unc(m);
 float lM=lum(m),lNW=lum(tap(uv+vec2(-1.,-1.)*px)),lNE=lum(tap(uv+vec2(1.,-1.)*px)),lSW=lum(tap(uv+vec2(-1.,1.)*px)),lSE=lum(tap(uv+vec2(1.,1.)*px));
 float lo=min(lM,min(min(lNW,lNE),min(lSW,lSE))),hi=max(lM,max(max(lNW,lNE),max(lSW,lSE)));
 if(hi-lo<max(.04,hi*.12))return unc(m);
 vec2 dir=vec2(-((lNW+lNE)-(lSW+lSE)),(lNW+lSW)-(lNE+lSE));
 float red=max((lNW+lNE+lSW+lSE)*.25*.125,1./128.);
 dir=clamp(dir/(min(abs(dir.x),abs(dir.y))+red),-8.,8.)*px;
 vec3 a=.5*(tap(uv+dir*(1./3.-.5))+tap(uv+dir*(2./3.-.5)));
 vec3 b=a*.5+.25*(tap(uv+dir*-.5)+tap(uv+dir*.5));
 float lb=lum(b);
 return unc((lb<lo||lb>hi)?a:b);
}
// contrast-adaptive sharpening on the compressed picture: a cross of four neighbours, weighted down where the local contrast is already high
vec3 sharpen(vec2 uv,vec3 base){
 if(uSharp<.01)return base;
 vec2 px=1./uRes;vec3 m=cmp(base);
 vec3 n=tap(uv+vec2(0.,px.y)),so=tap(uv-vec2(0.,px.y)),e=tap(uv+vec2(px.x,0.)),w=tap(uv-vec2(px.x,0.));
 vec3 mn=min(m,min(min(n,so),min(e,w))),mx=max(m,max(max(n,so),max(e,w)));
 vec3 amp=sqrt(clamp(min(mn,1.-mx)/max(mx,vec3(1e-4)),0.,1.));
 vec3 wt=-amp*mix(.08,.2,uSharp);
 vec3 r=(m+wt*(n+so+e+w))/(1.+4.*wt);
 return unc(clamp(r,0.,.999));
}
void main(){
 vec3 c=sharpen(vUV,scene(vUV))+texture(uBloom,vUV).rgb*uBloomK;
 c*=uExposure;
 vec2 d=vUV-.5;c*=1.-dot(d,d)*uLook.x;                     // vignette (picture style)
 c=aces(c);
 // colour grading: warm highlights, cool shadows, then the style's saturation and contrast
 float l=dot(c,vec3(.299,.587,.114));
 c=mix(c,c*vec3(1.+.03*uLook.w,1.0,1.-.04*uLook.w),smoothstep(.5,1.,l));
 c=mix(c,c*vec3(.96,.99,1.04),1.-smoothstep(0.,.35,l));
 c=max(mix(vec3(dot(c,vec3(.299,.587,.114))),c,uLook.y),0.);
 c=mix(c,c*c*(3.-2.*c),uLook.z);
 if(uRain>.01){
  float asp=uRes.x/uRes.y;float rs=0.;
  for(int i=0;i<3;i++){
   float fi=float(i);float sc=70.+fi*55.,sp=2.4+fi*1.1;
   vec2 q=vec2((vUV.x+vUV.y*.12)*asp*sc,vUV.y*sc*.1+uTime*sp+fi*3.7);
   vec2 id=floor(q),f=fract(q);float h=hash(id+fi*17.);
   float xx=abs(f.x-.15-h*.7),on=step(.45,h)*step(h,.45+uRain*.5);
   rs+=on*smoothstep(.07,.0,xx)*smoothstep(.0,.7,f.y)*(1.-f.y*.55)*(.9-fi*.2);
  }
  c=mix(c,c*.9,uRain*.4);c+=vec3(.62,.67,.75)*rs*uRainK*.55;
 }
 c=pow(c,vec3(1./2.2));
 c+=(hash(gl_FragCoord.xy)-.5)/255.;                      // dithering keeps the sky smooth
 oCol=vec4(c,1.);
}`;

