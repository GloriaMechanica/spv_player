// Titel: Alle meine Entchen in E-Dur
// Datum: 13.3.2021

#define $T1 4000 // ganze Note
#define $T2 2000 // halbe Note
#define $T4 1000 // viertel Note
#define $T8 500 // achtel Note
#define $T16 250 // sechzehntel Note

#define $POSE -18 // Position der E-Saite in Grad (Polarkoordinaten)
#define $DOWN -2 // Normaler Andruck des Bogens in mm

#begin
-300 pos_dae 5 $POSE
-300 str_dae 50
!300 e_note E5  // Viertelnote nach 100ms, zur “Vorbereitung”
+100 pos_dae $DOWN $POSE // Anstreichen auf der E-Saite

-0 str_dae 150 // Streichen bis genau zum nächsten Ton
!+$T4 e_note F5# // Nach einem Viertel eine weitere Note

-0 str_dae 50 // Wieder zurück streichen
!+$T4 e_note G5

-0 str_dae 150 // Wieder vorwärts
!+$T4 e_note A5
+20 pos_dae -4 $POSE // Hier wird kurz fester angedrückt. 
+300 pos_dae $DOWN $POSE
-0 str_dae 50
!+$T2 e_note B5

-0 str_dae 250 // Hier mehr stroke da es sich um eine längere Note handelt
!+$T2 e_note B5

$gaga