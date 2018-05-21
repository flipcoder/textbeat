" virtual edit for better column editing
au BufNewFile,BufRead *.dc set ve=all

" play file
au BufNewFile,BufRead *.dc let b:dispatch = '~/bin/decadence ' . shellescape(expand('%:p'),1)

" play note with <cr> key
au BufNewFile,BufRead *.dc noremap <cr> :Dispatch! ~/bin/decadence -l <C-R>=shellescape(getline('.'),1)<cr><cr>

