#include <stdio.h>

struct test_t {
	struct test_t *p;
};

void helloWorld( void ) {
  printf("Hello, world!\n");
  struct test_t test;
  test.p = &test;
  fprintf(stderr, "This is stderr output\n");
  // *(int volatile *)NULL = 42;
}
