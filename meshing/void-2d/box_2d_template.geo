lf = $INSERT_LF$;
h = 10;
l = 1.2*h;
r = h*0.1;
el = lf*h;

// inner circle:
Point(1) = {0.25*l,0.5*h,0,el};
Point(2) = {0.25*l+r,0.5*h,0,el};
Point(3) = {0.25*l,0.5*h+r,0,el};
Point(4) = {0.25*l-r,0.5*h,0,el};
Point(5) = {0.25*l,0.5*h-r,0,el};
Circle(1) = {2,1,3};
Line(101) = {1,2};
Circle(2) = {3,1,4};
Line(102) = {1,3};
Circle(3) = {4,1,5};
Line(103) = {1,4};
Circle(4) = {5,1,2};
Line(104) = {1,5};
Line Loop(1) = {101, 1, -102};
Line Loop(2) = {102, 2, -103};
Line Loop(3) = {103, 3, -104};
Line Loop(4) = {104, 4, -101};
Line Loop(105) = {2, 3, 4, 1};

// box points:
Point (6) = {0, 0, 0, el};
Point (7) = {l, 0, 0, el};
Point (8) = {l, h, 0, el};
Point (9) = {0, h, 0, el};
Line (5) = {9, 6};
Line (6) = {9, 8};
Line (7) = {6, 7};
Line (8) = {8, 7};
Line Loop (10) = {6, 8, -7, -5};
// Box surface:
Plane Surface(107) = {10, 105};

// Physical IDs:
//front/inlet:
Physical Line(1) = {5};
//top and bottom
Physical Line(2) = {6, 7};
//back/outlet:
Physical Line(3) = {8};
// Cylinder:
Physical Line(4) = {1, 2, 3, 4};
// Surface
Physical Surface(1) = {107};

