#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

#define LIMIT RLIMIT_DATA

int main(int argc, char **argv) {
  if (argc < 3) {
    printf("Usage: %s MEMORY_LIMIT PROGRAM [ARGUMENT]...\n", argv[0]);
    return 1;
  }

  rlim_t requested_limit = atoi(argv[1]);

  if (requested_limit == 0) {
    printf("Invalid MEMORY_LIMIT: %lu\n", requested_limit);
    return 1;
  }

  struct rlimit limit;
  getrlimit(LIMIT, &limit);

  if (requested_limit > limit.rlim_max) {
    printf("Cannot set a limit higher than the hard limit: %lu\n", limit.rlim_max);
    return 1;
  }

  limit.rlim_cur = requested_limit;
  if (setrlimit(LIMIT, &limit) != 0) {
    perror("setrlimit failed");
    return 1;
  }

  execvp(argv[2], argv + 2);

  // execvp only returns if it fails to replace the process
  perror("execvp failed");

  return 1;
}
