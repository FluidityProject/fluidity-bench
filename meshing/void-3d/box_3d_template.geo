lf = $INSERT_LF$;

// void square:
// Create square cylinder:
Point(101) = {0.45,0.15,0,lf};
Point(102) = {0.45,0.25,0,lf};
Point(103) = {0.55,0.25,0,lf};
Point(104) = {0.55,0.15,0,lf};
Line(101) = {101,102};
Line(102) = {102,103};
Line(103) = {103,104};
Line(104) = {104,101};
Point(111) = {0.45,0.15,0.4,lf};
Point(112) = {0.45,0.25,0.4,lf};
Point(113) = {0.55,0.25,0.4,lf};
Point(114) = {0.55,0.15,0.4,lf};
Line(111) = {111,112};
Line(112) = {112,113};
Line(113) = {113,114};
Line(114) = {114,111};
// Surfaces of square cylinder:
Line(121) = {101,111};
Line(122) = {102,112};
Line(123) = {103,113};
Line(124) = {104,114};
Line Loop(111) = {101, 102, 103, 104};
//Plane Surface(111) = {111};
Line Loop(112) = {111, 112, 113, 114};
//Plane Surface(112) = {112};
Line Loop(125) = {121, 111, -122, -101};
Plane Surface(126) = {125};
Line Loop(127) = {122, 112, -123, -102};
Plane Surface(128) = {127};
Line Loop(129) = {113, -124, -103, 123};
Plane Surface(130) = {129};
Line Loop(131) = {121, -114, -124, 104};
Plane Surface(132) = {131};

// box:
// front face:
Point(1) = {0,0,0,lf};
Point(2) = {0,0,0.4,lf};
Point(3) = {0,0.4,0.4,lf};
Point(4) = {0,0.4,0,lf};
// lines:
Line(1) = {1,2};
Line(2) = {2,3};
Line(3) = {3,4};
Line(4) = {4,1};
Line Loop(1) = {2, 3, 4, 1};
Plane Surface(1) = {1};
// back face:
Point(11) = {1,0,0,lf};
Point(12) = {1,0,0.4,lf};
Point(13) = {1,0.4,0.4,lf};
Point(14) = {1,0.4,0,lf};
// lines:
Line(11) = {11,12};
Line(12) = {12,13};
Line(13) = {13,14};
Line(14) = {14,11};
Line Loop(2) = {12, 13, 14, 11};
Plane Surface(2) = {2};
// connecting front and back face:
Line(21) = {1,11};
Line(22) = {2,12};
Line(23) = {3,13};
Line(24) = {4,14};
// surfaces for top/bottom/side walls:
Line Loop(133) = {3, 24, -13, -23};
Plane Surface(134) = {133};
Line Loop(135) = {1, 22, -11, -21};
Plane Surface(136) = {135};
Line Loop(137) = {22, 12, -23, -2};
Plane Surface(138) = {112, 137};
Line Loop(139) = {4, 21, -14, -24};
Plane Surface(140) = {111, 139};

// box volume:
Surface Loop(141) = {1, 138, 134, 140, 2, 136, 126, 132, 130, 128};
Volume(1) = {141};


// Physical IDs:
//front/inlet:
Physical Surface(1) = {1};
//sides:
Physical Surface(2) = {134, 136};
//top and bottom
Physical Surface(3) = {26, 30};
//back/outlet:
Physical Surface(4) = {2};
// cylinder:
Physical Surface(137) = {126, 132, 130, 128};

//volumes
Physical Volume(1) = {1};

