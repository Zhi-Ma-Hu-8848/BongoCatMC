#ifdef GL_ES
precision highp float;
precision highp int;
#elif __VERSION__ < 130
#define highp
#define mediump
#define lowp
#endif
