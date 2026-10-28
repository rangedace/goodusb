#include <Keyboard.h>

void setup() {
  delay(2000);

  Keyboard.begin(KeyboardLayout_fr_FR);

  // Win + R
  Keyboard.press(KEY_LEFT_GUI);
  Keyboard.press('r');
  delay(100);
  Keyboard.releaseAll();

  delay(500);

  // Lancer le programme
  Keyboard.println("cmd /k \"echo salut\"");

  Keyboard.end();
}

void loop() {
}
