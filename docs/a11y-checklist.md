# Manual screen-reader checklist (TalkBack and VoiceOver) — T8-04

For Kevin (or a staff member) to run on a real phone before release. Written by the Opus test writer (p8-tests),
2026-11-20. Automated checks (axe on every screen in both languages, 320 px reflow, 200 % text) run in CI
(`aprende/e2e/a11y.spec.ts`); this list covers what a machine cannot hear. Use the test person **Ana Torres** only.

## Before you start
- Android: Settings → Accessibility → TalkBack → On. Swipe right/left = next/previous item; double-tap = activate.
- iPhone: Settings → Accessibility → VoiceOver → On. Same gestures.
- Open the test site in Chrome (Android) or Safari (iPhone). Do each check in **Spanish**, then switch to **English** in
  Perfil and repeat the starred (★) ones.
- Mark each line: ✅ works, ❌ problem (write what you heard), — not tested. Note the phone model and system version.

Phone / system: ____________________   Date: ____________   Tester: ____________

## 1. Welcome and account
- [ ] ★ The first thing read is the title "Aprende y Planea", then La Calavera's welcome text.
- [ ] "Crear cuenta" and "Iniciar sesión" are read as **links** or **buttons** with those exact names.
- [ ] Every field in "Crear cuenta" says its name (Nombre, Correo electrónico, Contraseña) before you type.
- [ ] The adult check box says "mayor de 18" and whether it is checked.
- [ ] A wrong password is announced right away ("…no coinciden" or similar) without moving your finger.

## 2. Day-1 steps
- [ ] ★ La Calavera's message says he is an AI program, not the attorney and not a person, and it is read in full.
- [ ] The consent question is read, then the answer box, then "Responder".
- [ ] After "No, no acepto", the new screen's heading is read first ("Está bien. No guardamos nada.").
- [ ] In the names step, "Agregar otro nombre" adds a field and focus or the reading moves to the new field.
- [ ] The waiting screen says the office is checking the names, and nothing more.

## 3. Course map and lesson
- [ ] ★ The map reads "Día 1 de 14", the candle and petal counts with their words ("días seguidos", "pétalos"), and
      today's lesson with its "Empezar" link.
- [ ] Locked days say why they are locked ("Se abre después…").
- [ ] ★ In the lesson, the progress bar is read with its name ("Avance de la lección") and a value.
- [ ] The character's words are on screen and read as text (the 3D character itself is not read as clutter).
- [ ] Answer choices are read as radio buttons with their full text; the chosen one says "selected/seleccionado".
- [ ] ★ After "Comprobar", the result ("¡Muy bien!" or "Casi…") and the explanation are announced without searching.
- [ ] The source link is read with its section ("Código de Sucesiones… sección 6111").
- [ ] "Salir" leaves the lesson and the place is kept when you come back.
- [ ] With the system's **reduce motion** on, no celebration moves; a quiet card appears instead.

## 4. Tus datos, documents and summary
- [ ] Each question from the character is read, then the answer box, "Enviar" and "Saltar".
- [ ] "Pregunta 1 de 4" (the count) is read.
- [ ] The document choices are check boxes with their names; "No sé todavía" is read.
- [ ] In the summary, each answer is read with its question; "La saltó" is read for a skipped one.

## 5. Plan, payment, review, appointment, signed documents
- [ ] ★ "Mi plan": each step is read with its day, date and status; a late step is said in words, not only by colour.
- [ ] The price card reads each discount and the total.
- [ ] "Modo de prueba: no se cobra nada." is read on the payment page; "Pagar con Stripe" is a button.
- [ ] In "Revise sus documentos", each article summary is read; "Está bien" and "Pedir un cambio" are buttons.
- [ ] ★ In "Su cita", each time is a button with the day and time; the confirm window is announced as a dialog with its
      question, and focus starts on the safe choice.
- [ ] Closing the dialog returns you to the time you chose.
- [ ] Signed documents are links with the document name; the download works.

## 6. Preguntas and Perfil
- [ ] The attorney's answer is read after "Respuesta del abogado Raval:".
- [ ] ★ Perfil: "Idioma" is a list box; "Recordatorio diario" is read as a switch (on/off); "Hora del recordatorio" is
      read; "Instalar la aplicación" appears only when the phone can install it; "Cerrar sesión" is a button.

## 7. Text size and zoom
- [ ] Set the phone's text size to the largest. Every screen above still shows all its text without cutting words or
      needing to scroll sideways.
- [ ] Pinch zoom works on every screen (it is not blocked).

## 8. Chrome extension (desktop, with NVDA or ChromeVox if available)
- [ ] The popup reads the day, the streak and today's step, then "Abrir".
- [ ] The side panel reads the same as the phone app.

## Result
Problems found (screen, what you heard, what you expected):

1.
2.
3.

When done, commit this file with the marks filled in (or send it to the lead to commit).
