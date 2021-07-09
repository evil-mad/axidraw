from .axidraw_cli import axidraw_CLI

try:
    from .hta_cli import hta_CLI
except ImportError as ie:
    if "hta" in str(ie) or "hershey" in str(ie):
        # this is probably ok, because it just means hershey advanced is not available on this installation
        pass
    else:
        raise ie

def main():
    axidraw_CLI()

if __name__ == '__main__':
    main()
