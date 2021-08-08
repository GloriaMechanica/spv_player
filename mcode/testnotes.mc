// Titel: Alle meine Entchen in E-Dur
// Datum: 13.3.2021

#define $T1 1600 // ganze Note
#define $T2 2000 // halbe Note
#define $T4 500 // viertel Note
#define $T8 200 // achtel Note
#define $T16 100 // sechzehntel Note

#define $POSE 27 // Position der E-Saite in Grad (Polarkoordinaten)
#define $DOWN -2 // Normaler Andruck des Bogens in mm
#define $UP 5 // ruheposition

#begin
-300 pos_dae $UP $POSE
-300 str_dae 50
!300 e_note F5#  // Viertelnote nach 300ms, zur “Vorbereitung”
+100 pos_dae $DOWN $POSE // Anstreichen auf der E-Saite

-0 str_dae 150 // Streichen bis genau zum nächsten Ton
!+$T4 e_note G5# // Nach einem Viertel eine weitere Note

-0 str_dae 50 // Wieder zurück streichen
!+$T2 e_note E5










