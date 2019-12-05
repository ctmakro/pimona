from termcolor import colored, cprint
import colorama

colorama.init()

def colored_print_generator(*a,**kw):
    def colored_print(*items,**incase):
        text = ' '.join(map(lambda i:str(i), items))

        # escape unsupported unicode in current encoding
        # (to prevent emojis from crashing CMD
        text = text.encode(encoding='gbk', errors='replace').decode()

        print(colored(text, *a,**kw),**incase)
    return colored_print

if __name__ == '__main__':
    cpg = colored_print_generator
    printredcyan = cpg('red', 'on_cyan')

    printredcyan('red', 'on_cyan')
