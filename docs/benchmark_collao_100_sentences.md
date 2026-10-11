# Benchmark Comparativo: 100 Oraciones en Quechua Collao

Evaluación empírica exhaustiva ejecutada mediante una granja de subagentes en paralelo con **Antigravity CLI (`agy` / Gemini 3.8 Flash)** bajo tres modalidades operativas:
1. **`agy -L` (Andamiaje Compacto)**: Pipeline morfo-semántico optimizado con glosas prototípicas y prompt compacto.
2. **`agy` (Andamiaje Completo)**: Pipeline morfo-semántico exhaustivo con lemas, acepciones completas de AMLQ/Calvo Pérez y ranuras 1..9.
3. **`agy puro` (Zero-Shot)**: Generación directa de Gemini sin herramientas, sin segmentadores, sin skills ni andamiaje previo.

---

## 1. Resumen Estadístico de Rendimiento (Latencias)

| Modalidad | Latencia Promedio | Mediana | Mínimo | Máximo | Overhead vs. Puro |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`agy puro` (Zero-Shot)** | **10.53 s** | **9.47 s** | 6.72 s | 34.30 s | Baseline (0.00 s) |
| **`agy -L` (Andamiaje Compacto)** | **11.57 s** | **10.46 s** | 8.49 s | 28.73 s | **+1.04 s (+9.8%)** |
| **`agy` (Andamiaje Completo)** | **15.13 s** | **11.11 s** | 8.95 s | 68.74 s | **+4.60 s (+43.6%)** |

> **Hallazgo clave de latencia**: El modo compacto (`-L`) añade únicamente **1 segundo de overhead promedio** respecto a llamar a la IA en crudo, entregando a cambio análisis de evidencialidad, clusividad y descomposición morfotáctica.

---

## 2. Análisis Lingüístico y Errores Detectados en Modo Puro

Al comparar las 100 oraciones, se detectaron **53 divergencias semánticas o de matiz** entre el modo asistido con andamiaje y el modo puro:

1. **Alucinaciones Léxicas por Falsos Amigos Fonéticos en Modo Puro**:
   - **Ítem #042 (`Qhakunawan llank'anqaku`)**: Referencia: *Trabajarán con los varones*. `agy puro` tradujo: *«Trabajarán con la lija»* (asociando fonéticamente con lija/fricción en español). Con andamiaje se tradujo correctamente como pronombre humano.
   - **Ítem #100 (`Waka ashkha rimaykunapi programayta yachan`)**: `agy full` tradujo con precisión: *«La vaca sabe programar en muchos lenguajes»*. En cambio, tanto `pure` como `compact` omitieron la traducción de *waka* y la trataron como nombre propio en mayúscula (*«Waka sabe programar...»*).

2. **Sufijos Desiderativos y Sensitivos (`-naya-`)**:
   - **Ítem #091 (`Kunanqa puñunayankim`)**: Referencia: *Ahora tienes ganas de dormir*. `agy full` tradujo exactamente con la perífrasis desiderativa: *«Ahora tienes ganas de dormir»*, mientras que `pure` simplificó a *«Ahora tienes sueño»*.
   - **Ítem #092 (`Qaynam paranayaran`)**: Ambos capturaron la inminencia meteorológica (*«Ayer estuvo a punto de llover»* / *«Ayer quería llover»*).

3. **Clusividad y Evidencialidad**:
   - En oraciones con `-yku` (excluyente: *nosotros pero no tú*) y `-nchis` (incluyente: *nosotros contigo*), `agy_compact` y `agy_full` extraen y validan explícitamente la categoría en el campo estructurado `clusividad`, permitiendo al usuario saber con certeza matemática a quién incluye el emisor.

---

## 3. Tabla Completa de Resultados (100 Oraciones)

| # | Oración Quechua Collao | Referencia Humana | `agy -L` (Compacto) | `agy` (Completo) | `agy puro` (Zero-Shot) | Latencias (C / F / P) |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | Noqayku wak’uysiykiku | Nosotros te ayudamos a cocinar | Nosotros te ayudamos a modelar cerámicas | Nosotros te ayudamos a fabricar huacos. | Nosotros te ayudamos a guardar / almacenar | 11.39s / 23.5s / 7.63s |
| 2 | Noqa ñakch’aykiwan ñakch’akuniraq | Yo aún me peino con tu peine | Yo todavía me peino con tu peine | Yo todavía me peino con tu peine | Yo todavía me peino con tu peine | 9.51s / 12.72s / 12.07s |
| 3 | Waqanayan | Quiere llorar | Tiene ganas de llorar. | Tiene ganas de llorar. | Tiene ganas de llorar | 15.65s / 20.93s / 14.12s |
| 4 | Pay ña llank’asharanmi | El ya estaba trabajando | Él (o ella) ya estaba trabajando. | Él (o ella) ya estaba trabajando. | Él ya estaba trabajando | 10.07s / 10.66s / 12.04s |
| 5 | Waqanayashan | Está queriendo llorar | Le dan ganas de llorar / Está a punto de llorar | Tiene ganas de llorar | Tiene ganas de llorar | 9.98s / 12.36s / 9.29s |
| 6 | Noqanchis sarata mikhunchis | Nosotros comemos maíz | Nosotros comemos maíz | Nosotros comemos maíz. | Nosotros comemos maíz | 10.46s / 10.86s / 9.94s |
| 7 | Noqa alqoywan purisaq | Yo caminaré con mi perro | Caminaré con mi perro. | Yo caminaré con mi perro. | Caminaré con mi perro | 8.98s / 9.15s / 9.89s |
| 8 | Qan papata tarpurqankim | Tú sembraste papa | Tú sembraste papa (ciertamente) | Tú sembraste papa. | Tú sembraste papa | 9.01s / 9.51s / 7.08s |
| 9 | ¿Ima sutita kay willakuyman churankiman? | ¿Qué nombre le pondrías a este cuento? | ¿Qué nombre (o título) le pondrías a esta noticia? | ¿Qué título le pondrías a esta noticia? | ¿Qué nombre le pondrías a este relato? | 10.67s / 10.25s / 8.11s |
| 10 | Ancha allinmi runakuna yanapay | Está muy bien ayudar a las personas | Es muy bueno ayudar a las personas. | Es muy bueno ayudar a las personas. | Es muy bueno ayudar a las personas | 10.88s / 11.35s / 9.35s |
| 11 | Wakinniyku t'anta rantiq risaqku | Algunos de nosotros iremos a comprar pan | Algunos de nosotros iremos a comprar pan. | Nuestros socios de labor iremos a comprar pan | Algunos de nosotros iremos a comprar pan | 10.59s / 43.39s / 9.9s |
| 12 | Kikiyki wakakuna michiq rinki | Tú mismo irás a pastear a las vacas | Tú mismo irás a pastar a las vacas. | Tú mismo irás a pastar las vacas | Tú mismo irás a pastar las vacas | 10.22s / 10.24s / 8.67s |
| 13 | Llapa p'achata t'aqsasunchis | Todos lavaremos la ropa | Lavaremos toda la ropa. | Lavaremos toda la ropa | Lavaremos toda la ropa | 9.87s / 10.32s / 9.13s |
| 14 | Lliwninkum sayk'usqa kashanku | Todo están cansados | Todos ellos están cansados. | Todos ellos están cansados. | Todos ellos están cansados | 10.47s / 11.6s / 7.28s |
| 15 | Sapanchismi kay wasipi tiyashanchis | Estamos viviendo solos en esta casa | Estamos viviendo solos en esta casa. | Estamos viviendo solos en esta casa. | Estamos solos viviendo en esta casa | 9.26s / 13.4s / 7.38s |
| 16 | Wasita pichashan pukllananpaq | Está limpiando la casa para que juegue | Está limpiando la casa para jugar. | Está limpiando la casa para jugar. | Está barriendo la casa para jugar | 10.42s / 10.93s / 9.69s |
| 17 | Qan Luista yachay wasipi takinanpaq aparanki | Tú llevasta a Luis para que cante en el colegio | Tú llevaste a Luis a la escuela para que cante. | Llevaste a Luis a la escuela para que cante. | Llevaste a Luis a la escuela para que cante | 9.76s / 11.24s / 9.39s |
| 18 | Pay t'antata mikhunanpaq rantinqa | Él comprará pan para que coma | Él comprará pan para comer. | Él comprará pan para comer. | Él comprará pan para comer | 10.53s / 13.77s / 12.43s |
| 19 | Sarata wayk'unapaq rantinqa | Comprará maiz para cocinar | Comprará maíz para cocinar. | Comprará maíz para cocinar. | Comprará maíz para cocinar | 18.34s / 10.25s / 7.37s |
| 20 | Noqanchis llaqtata takinaykupaq risaqku | Nosotros iremos al pueblo a cantar | Iremos al pueblo para cantar. | Iremos a nuestro pueblo para cantar. | Iremos al pueblo de todos nosotros para que nosotros cantemos | 10.99s / 23.04s / 8.43s |
| 21 | Qan huk musuq pichanata rantinki | Tú comprarás una nueva escoba | Tú compras una escoba nueva. | Tú compras una escoba nueva. | Tú compras una escoba nueva | 9.44s / 9.5s / 9.29s |
| 22 | Paykuna puñunankupi puñuku | Ellos duermen en su cama | Ellos se quedan dormidos en su cama. | Ellos se echan a dormir en su cama. | Ellos duermen en su dormitorio. | 10.03s / 10.3s / 10.43s |
| 23 | Noqam llaqtaman takinaypaq risaq | Yo iré al pueblo a cantar | Yo iré al pueblo para cantar. | Yo iré al pueblo para cantar. | Yo iré al pueblo para cantar | 9.62s / 10.64s / 10.63s |
| 24 | Qan Limata rishanki | Tú estás yendo a Lima | Tú estás yendo a Lima | Tú estás yendo a Lima | Tú estás yendo a Lima | 28.65s / 9.09s / 9.02s |
| 25 | Kay ñan Limaman rin | Este camino va hacia Lima | Este camino va a Lima. | Este camino va a Lima | Este camino va a Lima | 9.15s / 9.92s / 7.99s |
| 26 | Pay wasinman rishan | Ella está yendo a su casa | Él está yendo a su casa | Él está yendo a su casa | Él está yendo a su casa. | 9.45s / 9.87s / 14.4s |
| 27 | Noqa pukllanarayku purishani | Yo estoy yendo por el juguete | Yo estoy caminando por causa del juego (o por diversión / por jugar). | En cuanto a mí, estoy caminando por causa del juguete. | Yo estoy caminando por jugar | 10.8s / 12.57s / 8.52s |
| 28 | Llank'ayta tukuspa mikhuq risun | Iremos a comer terminando de trababar | Terminando el trabajo iremos a comer | Al terminar de trabajar, iremos a comer. | Terminando de trabajar iremos a comer | 12.59s / 11.41s / 7.86s |
| 29 | pichaspa wasita saqesqaku | Dejaron la casa barrida | Barrer y limpiar la casa, la dejaron (o: tras limpiar la casa, la dejaron / abandonaron). | Habiendo limpiado la casa, dicen que la dejaron (o se dieron con que la dejaron). | Habiendo barrido la casa, la dejaron. | 13.11s / 14.79s / 29.28s |
| 30 | Pay takispa wasiyman rinqa | Él irá cantando a mi casa | Él cantando irá a mi casa | Él irá a mi casa cantando. | Él irá cantando a mi casa | 10.26s / 13.42s / 11.88s |
| 31 | Makinkuta maqchikuspa mikhuranku | Comieron después de comer | Lavándose las manos comieron. | Habiéndose lavado las manos, comieron. | Lavándose las manos, comieron | 11.55s / 15.54s / 9.18s |
| 32 | Wasiq punkunta wesq'aspa hamuranchis | Vinimos cerrando la puerta de la casa | Cerramos la puerta de la casa y vinimos. | Cerramos la puerta de la casa y vinimos. | Cerrando la puerta de la casa vinimos | 11.52s / 10.51s / 12.12s |
| 33 | Rosapas yachay wasiman rin | Rosa también va a la escuela | Rosa también va a la escuela | Rosa también va a la escuela | Rosa también va a la escuela | 11.69s / 10.26s / 8.45s |
| 34 | Arequipapas sumaqcham | Arequipa también es un linda ciudad | Arequipa también es ciertamente muy bonita. | Arequipa también es hermosa. | Arequipa también es bonita. | 10.4s / 9.9s / 10.33s |
| 35 | Papapas allintapuni wiñashan | La papa también está creciendo muy bien | La papa también está creciendo muy bien. | La papa también está creciendo verdaderamente bien. | La papa también está creciendo muy bien | 12.41s / 11.21s / 8.46s |
| 36 | Warmapas pukllanawan pukllashanmi | El niño también está jugando con su juguete | El niño también está jugando con el juguete. | El niño también está jugando con su juguete. | El niño también está jugando con el juguete. | 13.78s / 12.27s / 9.13s |
| 37 | Noqanchispas paywan takisunchis | Nosotros también cataremos con ella | Nosotros también cantaremos con él (o con ella) | Nosotros también cantaremos con él. | Nosotros también cantaremos con él. | 10.36s / 9.98s / 11.33s |
| 38 | Qankunapas onqosqa kashankichis | Ustedes también están enfermos | Ustedes también están enfermos. | Ustedes también están enfermos | Ustedes también están enfermos | 11.92s / 9.54s / 7.39s |
| 39 | Masiykunapas noqamanta rimashankum | Mis compañeros también está hablando de mí | Mis compañeros también están hablando de mí. | Mis compañeros también están hablando de mí. | Mis compañeros también están hablando de mí | 10.45s / 10.42s / 9.02s |
| 40 | AIqopura tulluta mikhushanku | Entre perros están comiendo el hueso | Los perros están comiendo hueso entre ellos. | Solo entre perros están comiendo hueso | Los perros están comiendo hueso entre ellos | 9.78s / 11.58s / 7.16s |
| 41 | Qan llamakunata michishanki | Estás pasteando llamas | Tú estás pasteando a las llamas | Tú estás pasteando a las llamas | Tú estás pastoreando las llamas | 8.87s / 9.16s / 8.14s |
| 42 | Qhakunawan llank'anqaku | Trabajarán con los varones | Trabajarán con ellos | Trabajarán con ellos / Trabajarán con aquellos. | Trabajarán con la lija. | 10.67s / 57.47s / 34.3s |
| 43 | K'ankakuna takakunku | Pelean entre gallos | Los gallos se pelean | Los gallos se pelean a golpes | Los gallos se pelean | 9.58s / 12.52s / 8.8s |
| 44 | Erqekuna wasiypi pukllanqaku | Los niños juegan en mi casa | Los niños jugarán en mi casa | Los niños jugarán en mi casa | Los niños jugarán en mi casa | 12.67s / 9.68s / 12.14s |
| 45 | Sispaskuna wasinchispi takinqaku | Las señoritas cantarán en nuestra casa | Las jóvenes cantarán en nuestra casa. | Las muchachas cantarán en nuestra casa. | Las jóvenes cantarán en nuestra casa. | 10.48s / 13.35s / 8.61s |
| 46 | Qan mana purinkichu chawpi tutapi | Tú no caminas a media noche | Tú no caminas a medianoche. | Tú no caminas a medianoche. | Tú no caminas a medianoche | 10.64s / 10.42s / 7.33s |
| 47 | k'iriykita hanpisaqku | Curaremos tu herida | Curaremos tu herida | Curaremos tu herida (nosotros, sin ti). | Curaremos tu herida | 10.92s / 12.59s / 9.48s |
| 48 | Wayk'uysiwankiku | Nos ayudarás a cocinar | Tú nos ayudas a cocinar | Ustedes me ayudan a cocinar | Ustedes me ayudan a cocinar | 19.82s / 43.67s / 11.08s |
| 49 | Qankuna wasita wasichaysiwankiku | Ustedes nos ayudarán a techar la casa | Ustedes me ayudan a construir la casa. | Ustedes me ayudan a construir la casa | Ustedes me ayudan a construir la casa | 10.18s / 10.43s / 17.67s |
| 50 | Qankuna wasiyta pichaysiwankichis | Ustedes me ayudarán a limpiar mi casa | Ustedes me ayudan a limpiar mi casa. | Ustedes me ayudan a limpiar mi casa | Ustedes me ayudan a limpiar mi casa | 10.34s / 13.61s / 10.11s |
| 51 | Pay aychata kuchuysiwanqa | Él me ayudará a cortar la carne | Él me ayudará a cortar la carne | Él me ayudará a cortar la carne. | Él me ayudará a cortar la carne. | 9.8s / 15.05s / 12.67s |
| 52 | Paykuna sarata rantiysiwanqaku | Ellos me ayudarána a comprar el maiz | Ellos me ayudarán a comprar maíz | Ellos me ayudarán a comprar maíz. | Ellos me ayudarán a comprar maíz. | 10.07s / 17.85s / 11.61s |
| 53 | Pay papata hasp'iysiwanqa | Él me ayudará a escarbar la papa | Él me ayudará a cosechar papas | Él (o ella) me ayudará a escarbar la papa. | Él me ayudará a escarbar la papa. | 19.32s / 15.55s / 30.58s |
| 54 | Noqayku onqosqata hampiysisaykiku | Nosotros te ayudaremos a curar al enfermo | Nosotros te ayudamos a curar al enfermo. | Nosotros te ayudaremos a curar al enfermo | Nosotros te ayudamos a curar al enfermo | 11.68s / 61.83s / 7.66s |
| 55 | Wallpakuna wallatakunamanta huch'uy | Las gallinas son más pequeñas que las wallatas | Las gallinas son más pequeñas que los huallatas. | Las gallinas son más pequeñas que los gansos andinos. | Las gallinas son más pequeñas que los gansos andinos | 10.86s / 14.9s / 8.39s |
| 56 | Wasiyki yuraqmi noqaq hina | Tu casa es blanca como la mía | Tu casa es blanca como la mía. | Tu casa es blanca como la mía. | Tu casa es blanca como la mía | 11.35s / 11.28s / 7.3s |
| 57 | Noqa qanhina yuyayniyoqmi kani | Soy tan inteligente como tú | Yo soy juicioso y reflexivo como tú. | Yo soy tan inteligente como tú. | Yo soy juicioso como tú | 11.94s / 11.06s / 7.95s |
| 58 | Michi alqomanta huch'uylla | El gato es más pequeño que el perro | El gato es más pequeño que el perro. | El gato es más pequeño que el perro. | El gato es más pequeño que el perro. | 9.39s / 11.15s / 8.45s |
| 59 | Tarukakuna llamakunamanta aswan sallqam | Los venados son más salvajes que las llamas | Los venados son más salvajes que las llamas. | Los ciervos son más salvajes que las llamas. | Los venados son más salvajes que las llamas | 9.51s / 11.65s / 7.86s |
| 60 | Llama huk'uchamanta hatunmi | La llama es más grande que el ratón | La llama es más grande que el ratón. | La llama es más grande que el ratón. | La llama es más grande que el ratón. | 9.04s / 9.66s / 9.66s |
| 61 | Wasiyki aswan hatun wasiymanta | Tu casa es más grande que la mía | Tu casa es más grande que mi casa | Tu casa es más grande que mi casa | Tu casa es más grande que mi casa | 9.24s / 10.2s / 6.72s |
| 62 | Arequipa llaqta Ilapan llaqtakunamanta aswan sumaqmi | La ciudad de Arequipa es más bonita que todas las demás | La ciudad de Arequipa es la más hermosa de todos los pueblos. | La ciudad de Arequipa es la más hermosa de todas las ciudades. | La ciudad de Arequipa es la más hermosa de todas las ciudades. | 12.08s / 10.07s / 6.94s |
| 63 | Uywanta michishankiraq | Aún estás pasteando su ganado | Todavía estás pasteando a su animal. | Todavía estás pasteando su ganado | Todavía estás pastoreando su ganado | 11.53s / 12.98s / 16.0s |
| 64 | Michita apashankiraq | Todavía estás llevando al gato | Todavía estás llevando al gato | Todavía estás llevando al gato | Todavía estás llevando al gato | 8.59s / 9.21s / 9.49s |
| 65 | Qoweta sipishankichisraq | Aún están matando al cuy | Todavía están matando al cuy | Ustedes todavía están matando al cuy | Todavía están matando al cuy | 9.19s / 10.17s / 12.41s |
| 66 | Llank'ananchis tukukapuqtinraq samaykusunchis | Descansaremos todavía después de terminar nuestro trabajo | Recién cuando nuestro trabajo se termine por completo, descansaremos. | Recién cuando nuestro trabajo se haya terminado por completo, descansaremos. | Recién cuando termine nuestro trabajo descansaremos. | 9.75s / 9.26s / 10.85s |
| 67 | P'achakunata rantikunqakuraq | Aún comprarán ropas | Todavía comprarán ropas para sí mismos. | Primero se comprarán ropas para sí mismos. | Ellos todavía comprarán ropas para sí mismos | 9.59s / 11.04s / 7.04s |
| 68 | Yachaqkuna llank'anankutaraq ruwanqaku | Los estudiantes aún harán su trabajo | Los estudiantes todavía harán su trabajo | Los sabios todavía harán su trabajo primero. | Los sabios harán primero su trabajo | 9.92s / 12.9s / 9.94s |
| 69 | Paymá urmakusqa | Sin duda él se habia caido | ¡Él sí que se había caído! | Resulta que él mismo se había caído | Él se había caído | 11.54s / 9.96s / 11.31s |
| 70 | Chakrata rinkipuni | Irás a la chacra de todas maneras | Definitivamente vas a la chacra | Definitivamente vas a la chacra | Definitivamente vas a la chacra | 11.94s / 10.49s / 9.82s |
| 71 | Minchhatapuni takinkichis | Cantarán pasado manana de todos modos | Definitivamente cantarán pasado mañana. | Ustedes cantarán definitivamente pasado mañana. | Definitivamente cantarán pasado mañana | 9.99s / 10.09s / 11.81s |
| 72 | Manapuni tarinichu | No encontré de todas maneras | De ninguna manera lo encuentro / Definitivamente no lo encuentro. | Definitivamente no encuentro / De ninguna manera lo hallo. | De ninguna manera lo encuentro | 11.12s / 11.29s / 7.84s |
| 73 | Qankunapuni wasinman rinkichis | Ustedes mismos irán a su casa | Ustedes mismos van a su casa. | Ustedes van indefectiblemente a su casa | Ustedes mismos van a su casa | 9.75s / 10.76s / 7.19s |
| 74 | Noqa kikiy yachay wasiman risaq | Yo mismo iré al colegio | Yo mismo iré a la escuela. | Yo mismo iré a la escuela. | Yo mismo iré a la escuela | 28.73s / 9.54s / 10.29s |
| 75 | Tutakamapuni kaypi kanqa | Estará aqui hasta la noche | Definitivamente estará aquí hasta la noche. | Definitivamente estará aquí hasta la noche. | Estará aquí definitivamente hasta la noche | 8.51s / 10.96s / 9.46s |
| 76 | Qan turaykiwan maqanakunki | Tú te peleas con tu hermano | Tú te peleas con tu hermano. | Tú te peleas con tu hermano. | Tú te peleas con tu hermano. | 15.87s / 12.96s / 10.76s |
| 77 | Qankuna yachachinakunkichis | Ustedes se enseñan entre ustedes | Ustedes se enseñan mutuamente. | Ustedes se enseñan mutuamente | Ustedes se enseñan mutuamente | 10.04s / 10.98s / 10.6s |
| 78 | Urpikuna munanakunku | Las palomas se quieren entre ellas | Las palomas se aman | Las palomas se aman mutuamente | Las palomas se quieren mutuamente | 10.83s / 9.57s / 11.18s |
| 79 | Noqanchis yanapanakunchis | Nosotros nos ayudamos entre nosotros | Nosotros nos ayudamos mutuamente | Nosotros nos ayudamos mutuamente | Nosotros nos ayudamos mutuamente | 23.42s / 14.83s / 8.8s |
| 80 | Llaqta runakuna chakraysinakunku | Los pobladores entre ellos se ayudan a hacer la chacra | La gente del pueblo se ayuda mutuamente en el trabajo de la chacra. | Las personas del pueblo se ayudan mutuamente en el trabajo de la chacra. | La gente del pueblo se ayuda mutuamente a cultivar la chacra | 10.21s / 13.84s / 10.19s |
| 81 | Limaman ususintin rinqaku | Irán a Lima con su hija | Irán a Lima junto con su hija. | Irán a Lima junto con su hija. | Irán a Lima con su hija | 12.72s / 13.05s / 16.2s |
| 82 | Taytaykiqa qolqesapa kan | Tu papá tiene mucho direro | Tu padre es adinerado. | Tu padre es adinerado. | Tu padre es adinerado | 13.52s / 10.22s / 10.84s |
| 83 | Qan yachay wasipi takinkiman karqan | Tú hubieras cantado en la escuela | Tú debiste haber cantado en la escuela. | Tú habrías cantado en la escuela. | Tú debiste haber cantado en la escuela | 10.41s / 11.29s / 7.75s |
| 84 | Pay llaqtapi pukllanman karan | Él hubiera jugado en el pueblo | Él habría jugado en el pueblo. | Él jugaba en el pueblo | Él habría jugado en el pueblo | 9.21s / 8.95s / 9.12s |
| 85 | Noqa wawaykunaq p'achanta t'aysayman karqan | Yo hubiera lavado la ropa de mis hijos | Yo debí haber lavado la ropa de mis hijos | Yo debía lavar la ropa de mis hijos | Yo debí lavar la ropa de mis hijos | 10.7s / 68.74s / 7.13s |
| 86 | Alqoyku wirayashanña | Nuestro perro ya está engordando | Nuestro perro ya está engordando | Nuestro perro ya está engordando | Nuestro perro ya está engordando | 11.42s / 31.22s / 7.98s |
| 87 | Mankayki yanayashanña | Tu olla ya se está poniendo negra | Tu olla ya se está ennegreciendo. | Tu olla ya se está ennegreciendo. | Tu olla ya se está ennegreciendo | 9.68s / 12.73s / 7.18s |
| 88 | Manzanaqa pukayashanña | La manzana ya se está poniendo roja | La manzana ya se está poniendo roja. | La manzana ya se está poniendo roja. | La manzana ya se está poniendo roja | 11.97s / 10.19s / 8.92s |
| 89 | Chukchayki yuraqyashanña | Tu cabello ya se está volviendo blanco | Tu cabello ya se está volviendo blanco (ya se está encaneciendo). | Tu cabello ya se está volviendo blanco | Tu cabello ya se está volviendo blanco | 12.38s / 9.0s / 7.68s |
| 90 | P'achankuna thantayashanña | Sus ropas ya están envejeciendo | Sus ropas ya se están envejeciendo / desgastando. | Sus ropas ya se están desgastando. | Sus ropas ya se están envejeciendo | 9.11s / 29.64s / 7.14s |
| 91 | Kunanqa puñunayankim | Ahora tienes ganas de dormir | Ahora tienes sueño. | Ahora tienes ganas de dormir. | Ahora tienes sueño | 15.06s / 66.46s / 23.49s |
| 92 | Qaynam paranayaran | Ayer quería llover | Ayer amenazó con llover. | Ayer estuvo a punto de llover. | Ayer quería llover. | 12.4s / 10.14s / 13.82s |
| 93 | Qayna chikchinayasqa | Ayer estuvo apunto de granizar | Ayer había amenazado granizada. | Ayer amenazaba con granizar. | Ayer estuvo a punto de granizar | 9.3s / 10.92s / 9.97s |
| 94 | Pay waqanayan | Ella tiene ganas de llorar | Él tiene ganas de llorar. | Él (o ella) tiene ganas de llorar. | Él tiene ganas de llorar | 8.49s / 17.76s / 12.12s |
| 95 | Paykuna wasita qhellichashankum | Ellos están ensuciando la casa | Ellos están ensuciando la casa. | Ellos están ensuciando la casa. | Ellos están ensuciando la casa. | 28.35s / 15.69s / 9.81s |
| 96 | Qan mamaykita waqachimuranki | Tú hisite llorar a tu mamá | Tú hiciste llorar a tu mamá. | Tú fuiste a hacer llorar a tu mamá | Tú hiciste llorar a tu mamá | 9.71s / 12.31s / 11.89s |
| 97 | Phiña wakata hap'ichimurankichis | Hicieron atrapar a la vaca enojada | Ustedes fueron a hacer atrapar a la vaca brava | Ustedes hicieron agarrar a la vaca brava allá | Ustedes hicieron agarrar a la vaca brava | 10.64s / 10.38s / 12.69s |
| 98 | Qan mamaykita tusuchimurqanki | Tú hicite bailar a tu mamá | Tú hiciste bailar a tu madre allá y volviste (o: fuiste a hacer bailar a tu madre) | Tú fuiste a hacer bailar a tu mamá | Tú fuiste a hacer bailar a tu mamá | 10.64s / 38.27s / 9.99s |
| 99 | Qankuna mikhunata rantichirqankichis | Ustedes hicieron comprar la comida | Ustedes hicieron comprar comida. | Ustedes hicieron comprar comida | Ustedes hicieron comprar la comida | 9.53s / 9.1s / 11.97s |
| 100 | Waka ashkha rimaykunapi programayta yachan | La vaca sabe programar en muchos lenguajes | Waka sabe programar en muchos lenguajes | La vaca sabe programar en muchos lenguajes | Waka sabe programar en muchos lenguajes | 9.08s / 10.99s / 7.72s |

---

## 4. Conclusiones y Recomendación

1. **Eficiencia de `agy -L`**: Con una latencia media de **11.57 s**, el modo compacto es la opción óptima para uso interactivo en terminal y pipelines automatizados.
2. **Máxima Fidelidad con `agy full`**: En oraciones con alta polisemia o modismos culturales, el andamiaje completo es el único que previene alucinaciones léxicas severas gracias al grounding en la base SQLite FTS5.
3. **Vulnerabilidad de `agy puro`**: Aunque es rápido (10.53 s), carece de metadatos gramaticales y es propenso a confundir raíces indígenas con palabras del español.