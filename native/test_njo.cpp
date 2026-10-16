#include "cmaj_NjohrrFiles.h"
#include <iostream>
#include <cassert>
using namespace njohrr;
static void show(const char* t,const std::string& s){ std::cout<<t<<": "<<s.substr(0,160)<<"\n"; }
int main(){
  show("info",handle("info","","",""));
  std::string data="Hello\0World\xff\x01 binary", d2(data.begin(),data.end());
  std::string payload; for(int i=0;i<1000;i++) payload+=char(i*7);
  auto b=b64encode(payload); std::string back; assert(b64decode(b,back)&&back==payload);
  for(std::string s: {"","a","ab","abc","abcd"}){ std::string r; assert(b64decode(b64encode(s),r)&&r==s);}
  show("write",handle("write","presets","Bass \xC3\xA4.njopreset",b64encode(payload)));
  show("write evil",handle("write","presets","../evil.txt","QQ=="));
  show("write evil2",handle("write","presets","a/b","QQ=="));
  show("write badkind",handle("write","..","x","QQ=="));
  show("list",handle("list","presets","",""));
  auto r=handle("read","presets","Bass \xC3\xA4.njopreset",""); show("read",r);
  auto p=r.find("\"data\":\"")+8; std::string back2; assert(b64decode(r.substr(p,r.rfind('"')-p),back2)&&back2==payload);
  show("move",handle("move","presets","Bass \xC3\xA4.njopreset","presets/Bass2.njopreset"));
  auto w1=handle("write","samples","k.wav","QQ=="); auto w2=handle("write","samples","k2.wav","QQ=="); show("move clash",handle("move","samples","k.wav","samples/k2.wav")); handle("delete","samples","k2.wav","");
  show("move kinds",handle("move","samples","k.wav","wavetables/k.wav"));
  show("list wt",handle("list","wavetables","",""));
  show("del",handle("delete","wavetables","k.wav",""));
  show("del missing",handle("delete","wavetables","k.wav",""));
  show("del presets",handle("delete","presets","Bass2.njopreset",""));
  show("list after",handle("list","presets","",""));
  std::cout<<"OK\n";
}
