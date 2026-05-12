#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

int main(int argc, char **argv)
{	
	FILE *file = NULL;
	char *inputFilename = NULL;
	char *outputFilename = NULL;
	unsigned char *buffer = NULL;
	size_t filesize = 0;
	int idx = 0;
	
	if(argc < 3)
	{
		printf("Usage: %s input_file output_file [search_term1 replacement_term1] ...\n", argv[0]);
		printf("Example: %s arm9.bin arm9_patched.bin nintendowifi.net 10.8.0.1\n", argv[0]);
		return 0;
	}
	
	inputFilename = argv[1];
	outputFilename = argv[2];
	
	// Calculate the number of custom search/replace pairs passed via CLI
	int custom_pairs = (argc - 3) / 2;
	int search_term_count = 1 + custom_pairs; // Base https:// -> http:// conversion is mandatory
	
	char **search_terms = malloc(search_term_count * sizeof(char*));
	char **replacement_terms = malloc(search_term_count * sizeof(char*));
	
	if (!search_terms || !replacement_terms) {
		printf("ERROR: Failed to allocate memory for terms.\n");
		return -3;
	}
	
	// Element 0: Mandatory SSL strip
	search_terms[0] = "https://";
	replacement_terms[0] = "http://";
	
	// Inject user-defined override pairs
	for (int i = 0; i < custom_pairs; i++) {
		search_terms[1 + i] = argv[3 + (i * 2)];
		replacement_terms[1 + i] = argv[4 + (i * 2)];
	}
	
	printf("Starting Sovereign ROM Patcher...\n");
	printf("Input: %s | Output: %s\n", inputFilename, outputFilename);
	for(int k = 0; k < search_term_count; k++) {
		printf("  Rule %d: '%s' -> '%s'\n", k + 1, search_terms[k], replacement_terms[k]);
	}
		
	file = fopen(inputFilename, "rb");
	if(!file)
	{
		printf("ERROR: Could not open %s for reading.\n", inputFilename);
		free(search_terms);
		free(replacement_terms);
		return -1;
	}
	
	fseek(file, 0, SEEK_END);
	filesize = ftell(file);
	rewind(file);
	
	buffer = (unsigned char*)calloc(filesize, sizeof(unsigned char));
	if(!buffer)
	{
		printf("ERROR: Could not create buffer with a size of %zu bytes.\n", filesize);
		fclose(file);
		free(search_terms);
		free(replacement_terms);
		return -2;
	}
	
	fread(buffer, 1, filesize, file);	
	fclose(file);
	
	int replaced_total = 0;
	
	// Search and perform safe byte-boundary replacement
	for(idx = 0; idx < search_term_count; idx++)
	{
		size_t i = 0;
		size_t search_term_len = strlen(search_terms[idx]);
		size_t replacement_term_len = strlen(replacement_terms[idx]);
		
		while(i < filesize)
		{
			if(i + search_term_len <= filesize && memcmp(buffer + i, search_terms[idx], search_term_len) == 0)
			{
				// Find the end of the string so we know how many bytes to move.
				// This assumes that all results are null-terminated.
				int len = strlen((char*)(buffer + i));
				char *p = (char*)(buffer + i);
				int n = 0;
				int doReplace = 1;
				
				// Search the end of the string to find out how many null
				// bytes we have to work with, just in case we plan on overwriting
				// more than originally was there.
				while(i + len + n < filesize && p[len + n] == '\0')
					n++;
					
				// Take into account that we need at least one null-terminator at the
				// end of the string.
				n--;				
				
				if(replacement_term_len > search_term_len)
				{
					// If the replacement term is longer than the term to be replaced,
					// calculate how much free space will be left over after replacement.
					int remainingSpace = n - (int)(replacement_term_len - search_term_len);
					
					// If the free space is less than 0 then it means it runs over the
					// final null-terminator, which would cause errors in-game.
					if(remainingSpace < 0)
						doReplace = 0;
				}
				
				if(doReplace)
				{
					// Build replacement string and do replacement.
					// This method takes into account the null-terminators, so it should be safe.					
					int newlen = len + n;
					char *b = (char*)calloc(newlen + 1, sizeof(char));
					
					memcpy(b, replacement_terms[idx], replacement_term_len);
					
					// Only copy original trailing characters if there are any left in original length
					if (len > (int)search_term_len) {
						memcpy(b + replacement_term_len, p + search_term_len, len - search_term_len);
					}
					
					printf("  [MATCH] Replaced '%s' with '%s' at offset 0x%08zx.\n", p, b, i);
					
					// Perform the buffer overwrite
					memcpy(p, b, newlen);
					free(b);
					replaced_total++;
				}
				else
				{
					printf("  [SKIP] Not enough free space to replace '%s' with '%s' at offset 0x%08zx.\n", search_terms[idx], replacement_terms[idx], i);
				}
				
				i += search_term_len;
			}
			else
			{		
				i++;
			}
		}
	}
	
	file = fopen(outputFilename, "wb");
	if(!file)
	{
		printf("ERROR: Could not open %s for writing.\n", outputFilename);
		free(buffer);
		free(search_terms);
		free(replacement_terms);
		return -1;
	}
	
	fwrite(buffer, 1, filesize, file);
	fclose(file);
	
	free(buffer);
	free(search_terms);
	free(replacement_terms);
	
	printf("Patcher finished. Total replacements executed: %d.\n", replaced_total);
	return 0;
}
