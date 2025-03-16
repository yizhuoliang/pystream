#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sys/time.h>
#include <string.h>
#include <unistd.h>
#include <math.h>

#include "hrperf_api.h"

#ifndef STREAM_TYPE
#define STREAM_TYPE double
#endif

STREAM_TYPE *a, *b, *c;

typedef enum {
    OP_COPY,
    OP_SCALE,
    OP_ADD,
    OP_TRIAD
} operation_t;

typedef struct {
    int thread_id;
    ssize_t start_index;
    ssize_t end_index;
    int num_iterations;     /* Used in fixed iteration mode */
    operation_t operation;
    STREAM_TYPE scalar;
    int runtime_mode;       /* Flag for runtime mode */
    double runtime_seconds; /* Runtime in seconds (for runtime mode) */
    int *total_iterations;  /* Pointer to track iterations (for runtime mode) */
} thread_data_t;

/* Global variables for timing and completion times */
struct timeval start_time;
double *thread_completion_times;

/* Function prototypes with noinline attribute */
__attribute__((noinline)) void array_copy(ssize_t start, ssize_t end);
__attribute__((noinline)) void array_scale(ssize_t start, ssize_t end, STREAM_TYPE scalar);
__attribute__((noinline)) void array_add(ssize_t start, ssize_t end);
__attribute__((noinline)) void array_triad(ssize_t start, ssize_t end, STREAM_TYPE scalar);
void validate(ssize_t start, ssize_t end, operation_t operation, STREAM_TYPE scalar);

void *thread_function(void *arg);

int main(int argc, char *argv[]) {
    int num_threads = 1;
    ssize_t array_size = 10000000;
    int num_iterations = 10;
    operation_t operation = OP_COPY;
    STREAM_TYPE scalar = 3.0;
    int use_hrperf = 0;    /* New flag for hrperf toggle */
    int silent_mode = 0;   /* New flag for silent mode */
    int runtime_mode = 0;  /* Flag for runtime mode */
    double runtime_seconds = 0.0; /* Runtime in seconds */

    int opt;
    while ((opt = getopt(argc, argv, "n:s:i:o:c:pqr:")) != -1) {
        switch (opt) {
            case 'n':
                num_threads = atoi(optarg);
                break;
            case 's':
                array_size = atoll(optarg);
                break;
            case 'i':
                num_iterations = atoi(optarg);
                break;
            case 'o':
                if (strcmp(optarg, "copy") == 0) {
                    operation = OP_COPY;
                } else if (strcmp(optarg, "scale") == 0) {
                    operation = OP_SCALE;
                } else if (strcmp(optarg, "add") == 0) {
                    operation = OP_ADD;
                } else if (strcmp(optarg, "triad") == 0) {
                    operation = OP_TRIAD;
                } else {
                    fprintf(stderr, "Unknown operation: %s\n", optarg);
                    exit(EXIT_FAILURE);
                }
                break;
            case 'c':
                scalar = atof(optarg);
                break;
            case 'p':       /* New option for hrperf toggle */
                use_hrperf = 1;
                break;
            case 'q':       /* New option for silent mode */
                silent_mode = 1;
                break;
            case 'r':       /* New option for runtime mode */
                runtime_mode = 1;
                runtime_seconds = atof(optarg);
                if (runtime_seconds <= 0) {
                    fprintf(stderr, "Runtime must be positive\n");
                    exit(EXIT_FAILURE);
                }
                break;
            default:
                fprintf(stderr, "Usage: %s -n num_threads -s array_size -i num_iterations -o operation -c scalar [-p] [-q] [-r runtime_seconds]\n", argv[0]);
                fprintf(stderr, "  -p: Use hrperf for performance measurement\n");
                fprintf(stderr, "  -q: Silent mode (no output)\n");
                fprintf(stderr, "  -r: Run for specified number of seconds instead of fixed iterations\n");
                exit(EXIT_FAILURE);
        }
    }

    // Check parameters
    if (num_threads < 1) {
        fprintf(stderr, "Number of threads must be at least 1\n");
        exit(EXIT_FAILURE);
    }
    if (array_size < 1) {
        fprintf(stderr, "Array size must be at least 1\n");
        exit(EXIT_FAILURE);
    }
    if (num_iterations < 1) {
        fprintf(stderr, "Number of iterations must be at least 1\n");
        exit(EXIT_FAILURE);
    }

    // Allocate arrays
    a = (STREAM_TYPE *) malloc(sizeof(STREAM_TYPE) * array_size);
    b = (STREAM_TYPE *) malloc(sizeof(STREAM_TYPE) * array_size);
    c = (STREAM_TYPE *) malloc(sizeof(STREAM_TYPE) * array_size);

    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "Failed to allocate arrays\n");
        exit(EXIT_FAILURE);
    }

    // Initialize arrays
    ssize_t j;
    for (j = 0; j < array_size; j++) {
        a[j] = 1.0;
        b[j] = 2.0;
        c[j] = 0.0;
    }

    // Allocate thread completion times array
    thread_completion_times = (double *) malloc(sizeof(double) * num_threads);
    if (thread_completion_times == NULL) {
        fprintf(stderr, "Failed to allocate thread completion times array\n");
        exit(EXIT_FAILURE);
    }

    // Create threads
    pthread_t *threads = (pthread_t *) malloc(sizeof(pthread_t) * num_threads);
    thread_data_t *thread_data = (thread_data_t *) malloc(sizeof(thread_data_t) * num_threads);

    if (threads == NULL || thread_data == NULL) {
        fprintf(stderr, "Failed to allocate thread structures\n");
        exit(EXIT_FAILURE);
    }

    // Divide the array among threads
    ssize_t chunk_size = array_size / num_threads;
    ssize_t remainder = array_size % num_threads;

    // Divide iterations among threads (for fixed iteration mode)
    int iterations_per_thread = num_iterations / num_threads;
    int iterations_remainder = num_iterations % num_threads;
    
    // Create counter for total iterations (used in runtime mode)
    int total_iterations_completed = 0;

    /* Start hrperf only if enabled */
    if (use_hrperf) {
        hrperf_start();
    }

    gettimeofday(&start_time, NULL);

    int i;
    for (i = 0; i < num_threads; i++) {
        thread_data[i].thread_id = i;
        thread_data[i].start_index = i * chunk_size;
        thread_data[i].end_index = (i == num_threads - 1) ? array_size : (i + 1) * chunk_size;
        thread_data[i].num_iterations = iterations_per_thread + (i < iterations_remainder ? 1 : 0);
        thread_data[i].operation = operation;
        thread_data[i].scalar = scalar;
        thread_data[i].runtime_mode = runtime_mode;
        thread_data[i].runtime_seconds = runtime_seconds;
        thread_data[i].total_iterations = &total_iterations_completed;
        int rc = pthread_create(&threads[i], NULL, thread_function, (void *)&thread_data[i]);
        if (rc) {
            fprintf(stderr, "Error creating thread %d\n", i);
            exit(EXIT_FAILURE);
        }
    }

    // Wait for threads to complete
    for (i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }

    /* Pause hrperf only if enabled */
    if (use_hrperf) {
        hrperf_pause();
    }

    // Calculate total elapsed time
    double max_elapsed_time = 0.0;
    for (i = 0; i < num_threads; i++) {
        if (thread_completion_times[i] > max_elapsed_time) {
            max_elapsed_time = thread_completion_times[i];
        }
    }

    // Calculate total bytes moved
    int num_arrays_accessed;
    switch (operation) {
        case OP_COPY:
        case OP_SCALE:
            num_arrays_accessed = 2;  // Each iteration touches two arrays
            break;
        case OP_ADD:
        case OP_TRIAD:
            num_arrays_accessed = 3;  // Each iteration touches three arrays
            break;
        default:
            num_arrays_accessed = 0;  // Should not happen
            break;
    }

    // Get the actual number of iterations performed
    int actual_iterations = runtime_mode ? total_iterations_completed : num_iterations;
    
    // Calculate total bytes moved: 
    // (actual iterations) × num_arrays_accessed × array_size × sizeof(STREAM_TYPE)
    ssize_t total_bytes_moved = (ssize_t)(actual_iterations) * 
                              num_arrays_accessed * array_size * sizeof(STREAM_TYPE);

    // Report results only if not in silent mode
    if (!silent_mode) {
        printf("Operation: %s\n", (operation == OP_COPY) ? "Copy" :
                              (operation == OP_SCALE) ? "Scale" :
                              (operation == OP_ADD) ? "Add" : "Triad");
        printf("Threads: %d\n", num_threads);
        printf("Array size: %zd\n", array_size);
        if (runtime_mode) {
            printf("Runtime mode: %g seconds\n", runtime_seconds);
            printf("Total iterations completed: %d\n", total_iterations_completed);
        } else {
            printf("Iterations per thread: %d\n", iterations_per_thread);
            printf("Total iterations: %d\n", num_iterations);
        }
        printf("Elapsed time: %f seconds\n", max_elapsed_time);
        
        // Corrected bandwidth calculation to report in MB/s
        printf("Bandwidth: %f MB/s\n", (total_bytes_moved / 1e6) / max_elapsed_time);
    }

    // Clean up
    free(a);
    free(b);
    free(c);
    free(threads);
    free(thread_data);
    free(thread_completion_times);

    return 0;
}

__attribute__((noinline)) void array_copy(ssize_t start, ssize_t end) {
    ssize_t j;
    for (j = start; j < end; j++) {
        c[j] = a[j];
    }
}

__attribute__((noinline)) void array_scale(ssize_t start, ssize_t end, STREAM_TYPE scalar) {
    ssize_t j;
    for (j = start; j < end; j++) {
        b[j] = scalar * c[j];
    }
}

__attribute__((noinline)) void array_add(ssize_t start, ssize_t end) {
    ssize_t j;
    for (j = start; j < end; j++) {
        c[j] = a[j] + b[j];
    }
}

__attribute__((noinline)) void array_triad(ssize_t start, ssize_t end, STREAM_TYPE scalar) {
    ssize_t j;
    for (j = start; j < end; j++) {
        a[j] = b[j] + scalar * c[j];
    }
}

void validate(ssize_t start, ssize_t end, operation_t operation, STREAM_TYPE scalar) {
    const double epsilon = 1e-6;
    ssize_t j;
    switch (operation) {
        case OP_COPY:
            for (j = start; j < end; j++) {
                if (fabs(c[j] - a[j]) > epsilon) {
                    fprintf(stderr, "Validation failed at index %zd: c[%zd]=%f != a[%zd]=%f\n", j, j, c[j], j, a[j]);
                    exit(EXIT_FAILURE);
                }
            }
            break;
        case OP_SCALE:
            for (j = start; j < end; j++) {
                if (fabs(b[j] - scalar * c[j]) > epsilon) {
                    fprintf(stderr, "Validation failed at index %zd: b[%zd]=%f != scalar*c[%zd]=%f\n", j, j, b[j], j, scalar * c[j]);
                    exit(EXIT_FAILURE);
                }
            }
            break;
        case OP_ADD:
            for (j = start; j < end; j++) {
                if (fabs(c[j] - (a[j] + b[j])) > epsilon) {
                    fprintf(stderr, "Validation failed at index %zd: c[%zd]=%f != a[%zd]+b[%zd]=%f\n", j, j, c[j], j, j, a[j] + b[j]);
                    exit(EXIT_FAILURE);
                }
            }
            break;
        case OP_TRIAD:
            for (j = start; j < end; j++) {
                if (fabs(a[j] - (b[j] + scalar * c[j])) > epsilon) {
                    fprintf(stderr, "Validation failed at index %zd: a[%zd]=%f != b[%zd]+scalar*c[%zd]=%f\n", j, j, a[j], j, j, b[j] + scalar * c[j]);
                    exit(EXIT_FAILURE);
                }
            }
            break;
        default:
            fprintf(stderr, "Unknown operation in validation\n");
            exit(EXIT_FAILURE);
    }
}

void *thread_function(void *arg) {
    extern struct timeval start_time;
    extern double *thread_completion_times;
    struct timeval current_time;
    thread_data_t *data = (thread_data_t *)arg;
    int i = 0;
    
    if (data->runtime_mode) {
        // Runtime mode: Run until time is up
        double elapsed_time = 0.0;
        
        while (1) {
            // Perform operation
            switch (data->operation) {
                case OP_COPY:
                    array_copy(data->start_index, data->end_index);
                    break;
                case OP_SCALE:
                    array_scale(data->start_index, data->end_index, data->scalar);
                    break;
                case OP_ADD:
                    array_add(data->start_index, data->end_index);
                    break;
                case OP_TRIAD:
                    array_triad(data->start_index, data->end_index, data->scalar);
                    break;
                default:
                    fprintf(stderr, "Unknown operation\n");
                    return(NULL);
            }
            
            i++;
            
            // Check if runtime is reached
            gettimeofday(&current_time, NULL);
            elapsed_time = (current_time.tv_sec - start_time.tv_sec) + 
                          (current_time.tv_usec - start_time.tv_usec) / 1e6;
            
            // Atomic increment of completed iterations - this is just a rough count
            __sync_fetch_and_add(data->total_iterations, 1);
            
            if (elapsed_time >= data->runtime_seconds) {
                break;
            }
        }
    } else {
        // Fixed iterations mode (original behavior)
        for (i = 0; i < data->num_iterations; i++) {
            switch (data->operation) {
                case OP_COPY:
                    array_copy(data->start_index, data->end_index);
                    break;
                case OP_SCALE:
                    array_scale(data->start_index, data->end_index, data->scalar);
                    break;
                case OP_ADD:
                    array_add(data->start_index, data->end_index);
                    break;
                case OP_TRIAD:
                    array_triad(data->start_index, data->end_index, data->scalar);
                    break;
                default:
                    fprintf(stderr, "Unknown operation\n");
                    return(NULL);
            }
        }
    }

    // Record completion time
    gettimeofday(&current_time, NULL);
    double elapsed_time = (current_time.tv_sec - start_time.tv_sec) + (current_time.tv_usec - start_time.tv_usec) / 1e6;
    thread_completion_times[data->thread_id] = elapsed_time;

    // Validation pass
    validate(data->start_index, data->end_index, data->operation, data->scalar);

    return(NULL);
}
