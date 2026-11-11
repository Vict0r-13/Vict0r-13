/* Compatibility with older Android System WebView (modern JS syntax still required). */
if(!Array.prototype.at)Object.defineProperty(Array.prototype,'at',{value:function(index){let i=Math.trunc(Number(index)||0);if(i<0)i+=this.length;return this[i];},writable:true,configurable:true});
if(!crypto.randomUUID)crypto.randomUUID=function(){const b=new Uint8Array(16);crypto.getRandomValues(b);b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=Array.from(b,n=>n.toString(16).padStart(2,'0')).join('');return h.slice(0,8)+'-'+h.slice(8,12)+'-'+h.slice(12,16)+'-'+h.slice(16,20)+'-'+h.slice(20);};
