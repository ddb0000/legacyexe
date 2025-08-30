function lcsLines(A,B){
  const m=A.length,n=B.length,dp=Array.from({length:m+1},()=>Array(n+1).fill(0))
  for(let i=1;i<=m;i++)for(let j=1;j<=n;j++)
    dp[i][j]=A[i-1]===B[j-1]?dp[i-1][j-1]+1:Math.max(dp[i-1][j],dp[i][j-1])
  const out=[];let i=m,j=n
  while(i>0&&j>0){
    if(A[i-1]===B[j-1]){out.push({t:" ",v:A[i-1]});i--;j--}
    else if(dp[i-1][j]>=dp[i][j-1]){out.push({t:"-",v:A[i-1]});i--}
    else{out.push({t:"+",v:B[j-1]});j--}
  }
  while(i>0){out.push({t:"-",v:A[i-1]});i--}
  while(j>0){out.push({t:"+",v:B[j-1]});j--}
  return out.reverse()
}
export function unifiedDiff(a,b){
  const A=String(a||"").split("\n"),B=String(b||"").split("\n")
  const seq=lcsLines(A,B)
  const lines = ["--- antes","+++ depois",...seq.map(x=>`${x.t} ${x.v}`)]
  return lines.join("\n")
}
